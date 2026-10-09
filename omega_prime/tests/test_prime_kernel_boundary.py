# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""The kernel tools decode through a typed, versioned boundary (CONN-01).

Every case goes through ``ToolRegistry.dispatch`` with real ``ApprovalLog``
grants by a named reviewer. A rejected request returns its typed error code
and has no side effect: the kernel is never built, so the root stays empty
(the kernel creates ``prime-kernel`` on first use).
"""

from __future__ import annotations

import json

import pytest

from omega_prime.prime.kernel import (
    SCHEMA_VERSION,
    AutonomousCommandRequest,
    BashRequest,
    CellRequest,
    CratesRequest,
    FactoryGraphRequest,
    FactoryRunRequest,
    GoalCommandRequest,
    RunRequest,
    SkillListRequest,
)
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.prime_runtime import (
    KERNEL_TOOL_NAMES,
    register_prime_kernel_tools,
)
from omega_prime.tools.registry import ToolRegistry

_WRITE_TOOLS = (
    "prime_cell",
    "prime_factory_run",
    "prime_factory_stop",
    "prime_factory_resume",
    "prime_bash",
    "prime_goal",
    "prime_autonomous",
)

_VALID_ARGS: dict[str, dict] = {
    "prime_cell": {"code": "x = 1"},
    "prime_factory_run": {"spec_id": "spec"},
    "prime_factory_status": {"run_id": "run-1"},
    "prime_factory_stop": {"run_id": "run-1"},
    "prime_factory_resume": {"run_id": "run-1"},
    "prime_factory_graph": {},
    "prime_bash": {"command": "echo hi"},
    "prime_skill_list": {},
    "prime_crates": {},
    "prime_goal": {"args": "status"},
    "prime_autonomous": {"args": "status"},
}


def _registry(root, *, granted: bool = True) -> ToolRegistry:
    """Kernel tools on ``root``; write tools carry real human grants."""
    log = ApprovalLog()
    if granted:
        for name in _WRITE_TOOLS:
            receipt = log.approve(name, "phase61-human-reviewer")
            assert receipt["approved"] is True
    registry = ToolRegistry(approval_log=log)
    register_prime_kernel_tools(registry, root)
    return registry


def _dispatch(registry: ToolRegistry, name: str, arguments: dict) -> dict:
    return json.loads(registry.dispatch(name, arguments))


def _assert_rejected(tmp_path, result: dict, code: str) -> None:
    assert result["code"] == code
    assert "error" in result
    # No kernel, factory directory or any other file was created.
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("tool", _WRITE_TOOLS)
def test_unapproved_write_tool_is_denied_before_decode(tmp_path, tool):
    registry = _registry(tmp_path, granted=False)
    malformed = {"code": 5, "bogus": True, "schema_version": 9}

    result = _dispatch(registry, tool, malformed)

    assert result["error"] == "approval required"
    assert "code" not in result
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("prime_cell", {"code": 5}),
        ("prime_factory_run", {"spec_id": 5}),
        ("prime_factory_run", {"spec_id": "spec", "name": 5}),
        ("prime_factory_status", {"run_id": 5}),
        ("prime_factory_stop", {"run_id": ["run-1"]}),
        ("prime_factory_resume", {"run_id": None}),
        ("prime_factory_graph", {"ref": 5}),
        ("prime_bash", {"command": 5}),
        ("prime_goal", {"args": 5}),
        ("prime_autonomous", {"args": {"mode": "status"}}),
        ("prime_cell", {}),
        ("prime_factory_run", {}),
        ("prime_factory_status", {}),
        ("prime_factory_stop", {}),
        ("prime_factory_resume", {}),
        ("prime_bash", {}),
        ("prime_goal", {}),
        ("prime_autonomous", {}),
    ],
)
def test_wrong_type_or_missing_field_is_a_typed_error(tmp_path, tool, arguments):
    result = _dispatch(_registry(tmp_path), tool, arguments)

    _assert_rejected(tmp_path, result, "bad_type")


@pytest.mark.parametrize("tool", KERNEL_TOOL_NAMES)
def test_undeclared_field_is_rejected_not_silently_dropped(tmp_path, tool):
    arguments = {**_VALID_ARGS[tool], "bogus": 1}

    result = _dispatch(_registry(tmp_path), tool, arguments)

    _assert_rejected(tmp_path, result, "unknown_field")


@pytest.mark.parametrize("tool", KERNEL_TOOL_NAMES)
def test_future_schema_version_is_rejected(tmp_path, tool):
    arguments = {**_VALID_ARGS[tool], "schema_version": 2}

    result = _dispatch(_registry(tmp_path), tool, arguments)

    _assert_rejected(tmp_path, result, "unsupported_schema_version")


@pytest.mark.parametrize("tool", KERNEL_TOOL_NAMES)
def test_non_positive_schema_version_is_rejected(tmp_path, tool):
    arguments = {**_VALID_ARGS[tool], "schema_version": 0}

    result = _dispatch(_registry(tmp_path), tool, arguments)

    _assert_rejected(tmp_path, result, "bad_value")


def test_read_only_skill_list_still_returns_the_skills(tmp_path):
    result = _dispatch(_registry(tmp_path), "prime_skill_list", {})

    assert isinstance(result["skills"], list)
    assert result["skills"]
    for row in result["skills"]:
        assert {"name", "importable", "package"} <= set(row)
    assert list(tmp_path.iterdir()) == []


def test_current_schema_version_is_accepted(tmp_path):
    registry = _registry(tmp_path)

    plain = _dispatch(registry, "prime_skill_list", {})
    versioned = _dispatch(registry, "prime_skill_list", {"schema_version": 1})

    assert versioned == plain
    assert "code" not in versioned


def test_read_only_crates_still_reports_the_workspace(tmp_path):
    result = _dispatch(_registry(tmp_path), "prime_crates", {})

    assert isinstance(result["loaded"], bool)
    assert isinstance(result["crates"], list)
    assert result["crates"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "request_",
    [
        CellRequest(code="x = 1"),
        FactoryRunRequest(spec_id="spec"),
        FactoryRunRequest(spec_id="spec", name="nightly"),
        RunRequest(run_id="run-1"),
        FactoryGraphRequest(),
        FactoryGraphRequest(ref="spec"),
        BashRequest(command="echo hi"),
        SkillListRequest(),
        CratesRequest(),
        GoalCommandRequest(args="status"),
        GoalCommandRequest(args=""),
        AutonomousCommandRequest(args="on --max-turns 5"),
        AutonomousCommandRequest(args=""),
    ],
)
def test_request_round_trips_through_its_versioned_dict(request_):
    wire = request_.to_dict()

    assert wire["schema_version"] == SCHEMA_VERSION
    assert type(request_).from_dict(wire) == request_
