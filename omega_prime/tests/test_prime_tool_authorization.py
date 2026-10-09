# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Authorization precedes typed decoding for every Prime write tool (WR-14).

Each case registers one family through its real ``register_*`` function and
dispatches a malformed payload through ``ToolRegistry.dispatch``. A policy that
forbids the tool or a missing approval grant must answer first, with no side
effect and a ``denied`` audit verdict; only a real ``ApprovalLog`` grant by a
named reviewer lets the typed decoder run, and its failure is a structured
``code`` envelope audited as ``error``, never as ``allowed``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from omega_prime.agent.messaging import SessionRegistry
from omega_prime.audit.log import AuditLog
from omega_prime.policy.policy import SeatPolicy
from omega_prime.tools.agent_message import (
    MESSAGING_TOOL_NAMES,
    register_messaging_tools,
)
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.autonomous import (
    AUTONOMOUS_TOOL_NAMES,
    register_autonomous_tools,
)
from omega_prime.tools.goals import GOAL_TOOL_NAMES, register_goal_tools
from omega_prime.tools.harness import HARNESS_TOOL_NAMES, register_harness_tools
from omega_prime.tools.heartbeat import HEARTBEAT_TOOL_NAMES, register_heartbeat_tools
from omega_prime.tools.prime_runtime import (
    KERNEL_TOOL_NAMES,
    register_prime_kernel_tools,
)
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.rlm import RLM_TOOL_NAMES, register_rlm_tools

REVIEWER = "phase61-human-reviewer"

# A state probe: called after registration for a baseline, and again after a
# dispatch. Equal values mean the tool left no trace.
_Observe = Callable[[], Any]


class _RlmParent:
    """The RLM parent contract and nothing else."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = str(session_dir)
        self.session_name: str | None = None
        self.delegate_depth = 0
        self.max_depth = 2
        self.max_children = 4


def _tree(root: Path) -> list[str]:
    """Every path written under ``root``, relative and sorted."""
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


def _dir(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    return root


def _build_rlm(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    session_dir = _dir(tmp_path, "rlm-session")
    register_rlm_tools(registry, _RlmParent(session_dir))
    return lambda: _tree(session_dir)


def _build_harness(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    root = _dir(tmp_path, "harness-root")
    register_harness_tools(registry, root)
    return lambda: _tree(root)


def _build_goals(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    root = _dir(tmp_path, "goals-root")
    register_goal_tools(registry, root)
    return lambda: _tree(root)


def _build_autonomous(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    register_autonomous_tools(registry, _dir(tmp_path, "autonomous-root"))
    return lambda: json.loads(registry.dispatch("autonomous_status"))


def _build_messaging(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    sessions = SessionRegistry()
    register_messaging_tools(registry, "sender", session_registry=sessions)
    sessions.register("peer")
    return lambda: sessions.observe("peer", mark_read=False)


def _build_heartbeat(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    root = _dir(tmp_path, "heartbeat-root")
    register_heartbeat_tools(registry, root)
    return lambda: _tree(root)


def _build_kernel(registry: ToolRegistry, tmp_path: Path) -> _Observe:
    root = _dir(tmp_path, "kernel-root")
    register_prime_kernel_tools(registry, root)
    return lambda: _tree(root)


@dataclass(frozen=True)
class _Case:
    tool: str
    family: tuple[str, ...]
    build: Callable[[ToolRegistry, Path], _Observe]
    malformed: dict[str, Any]
    code: str
    valid: dict[str, Any] | None = None


_CASES = [
    _Case(
        "rlm_spawn",
        RLM_TOOL_NAMES,
        _build_rlm,
        {"prompt": 1, "name": "kid"},
        "bad_type",
    ),
    _Case(
        "harness_upsert",
        HARNESS_TOOL_NAMES,
        _build_harness,
        {"kind": "nope", "id": "x", "title": "t", "body": "b"},
        "bad_value",
        {"kind": "memory", "id": "x", "title": "t", "body": "b"},
    ),
    _Case(
        "goal_set",
        GOAL_TOOL_NAMES,
        _build_goals,
        {"objective": 5},
        "bad_type",
        {"objective": "ship the release"},
    ),
    _Case(
        "autonomous_start",
        AUTONOMOUS_TOOL_NAMES,
        _build_autonomous,
        {"max_turns": True},
        "bad_type",
    ),
    _Case(
        "agent_message_send",
        MESSAGING_TOOL_NAMES,
        _build_messaging,
        {"recipient": 3, "body": "x"},
        "bad_type",
        {"recipient": "peer", "body": "hello"},
    ),
    _Case(
        "heartbeat_set",
        HEARTBEAT_TOOL_NAMES,
        _build_heartbeat,
        {"session": "s", "prompt": "p", "interval_seconds": "soon"},
        "bad_type",
    ),
    _Case(
        "prime_cell",
        KERNEL_TOOL_NAMES,
        _build_kernel,
        {"code": 5},
        "bad_type",
    ),
]
_VALID_CASES = [case for case in _CASES if case.valid is not None]


def _name(case: _Case) -> str:
    return case.tool


def _seat(registry_tools: tuple[str, ...], forbidden: str) -> SeatPolicy:
    allowed = [name for name in registry_tools if name != forbidden]
    return SeatPolicy({"version": 1, "tools": {"allow": allowed}})


def _approvals(*tools: str) -> ApprovalLog:
    log = ApprovalLog()
    for tool in tools:
        receipt = log.approve(tool, REVIEWER)
        assert receipt["approved"] is True
    return log


def _dispatch(
    case: _Case,
    tmp_path: Path,
    arguments: dict[str, Any],
    *,
    granted: bool,
    forbid: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any, Any]:
    """One dispatch: ``(result, audit rows for the tool, before, after)``."""
    audit = AuditLog(tmp_path / "audit" / "audit.ndjson")
    registry = ToolRegistry(
        approval_log=_approvals(case.tool) if granted else ApprovalLog(),
        policy=_seat(case.family, case.tool) if forbid else None,
        audit=audit,
    )
    observe = case.build(registry, tmp_path)
    before = observe()
    result = json.loads(registry.dispatch(case.tool, arguments))
    rows = [row for row in audit.records() if row["tool"] == case.tool]
    return result, rows, before, observe()


@pytest.mark.parametrize("case", _CASES, ids=_name)
def test_policy_forbidding_a_write_tool_answers_before_decode(
    case: _Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result, rows, before, after = _dispatch(
        case, tmp_path, case.malformed, granted=True, forbid=True
    )

    assert result["tool"] == case.tool
    assert "code" not in result
    assert [row["verdict"] for row in rows] == ["denied"]
    assert after == before


@pytest.mark.parametrize("case", _CASES, ids=_name)
def test_missing_approval_answers_before_decode(
    case: _Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result, rows, before, after = _dispatch(
        case, tmp_path, case.malformed, granted=False
    )

    assert result["tool"] == case.tool
    assert "code" not in result
    assert [row["verdict"] for row in rows] == ["denied"]
    assert after == before


@pytest.mark.parametrize("case", _CASES, ids=_name)
def test_granted_malformed_payload_is_a_typed_error_audited_as_error(
    case: _Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result, rows, before, after = _dispatch(
        case, tmp_path, case.malformed, granted=True
    )

    assert result["code"] == case.code
    assert result["error"].startswith(f"{case.code}:")
    assert [row["verdict"] for row in rows] == ["error"]
    assert rows[0]["reason"].startswith(f"{case.code}:")
    assert after == before


@pytest.mark.parametrize("case", _VALID_CASES, ids=_name)
def test_granted_valid_payload_runs_and_is_audited_allowed(
    case: _Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert case.valid is not None

    result, rows, before, after = _dispatch(case, tmp_path, case.valid, granted=True)

    assert "error" not in result
    assert [row["verdict"] for row in rows] == ["allowed"]
    assert after != before
