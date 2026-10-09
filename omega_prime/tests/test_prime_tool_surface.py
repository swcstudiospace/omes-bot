# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Harness and autonomous tool surfaces through their real consuming paths.

Every case dispatches through ``ToolRegistry.dispatch`` (or the real
``OmegaPrimeAgent.run`` with a scripted model) against genuinely registered
tools. Approval comes from real ``ApprovalLog`` grants by a named reviewer.
The cases pin what a caller can observe: an undeclared ``scope`` key never
reaches the cross-session store, a typed failure is audited as an error, and
a non-finite autonomous time budget never starts a run.
"""

from __future__ import annotations

import json

import pytest

from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.audit.log import AuditLog
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.autonomous import (
    AUTONOMOUS_TOOL_NAMES,
    register_autonomous_tools,
)
from omega_prime.tools.harness import HARNESS_TOOL_NAMES, register_harness_tools
from omega_prime.tools.registry import ToolRegistry

_IDLE = {"running": False, "stopped": None}
_ENTRY = {"kind": "memory", "id": "note-1", "title": "t", "body": "b"}


def _granted(*families, audit=None):
    """A registry whose tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for family in families:
        for name in family:
            receipt = log.approve(name, "phase61-human-reviewer")
            assert receipt["approved"] is True
    return ToolRegistry(approval_log=log, audit=audit)


def _tool_call(name, arguments="{}", call_id="call-1"):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    }


def _run(registry, script, *, max_iterations=10):
    agent = OmegaPrimeAgent(
        ScriptedModel(script),
        registry=registry,
        system_message="SYS",
        max_iterations=max_iterations,
    )
    result = agent.run("go")
    return agent, result


def _model_tool_payload(agent, call_id):
    message = next(
        row
        for row in agent.provider_model.seen[-1]
        if row.get("role") == "tool" and row.get("tool_call_id") == call_id
    )
    return json.loads(message["content"])


def _tool_row(agent, call_id):
    """The raw tool-row text; a rejected call renders as ``error: ...``, not JSON."""
    return next(
        row["content"]
        for row in agent.provider_model.seen[-1]
        if row.get("role") == "tool" and row.get("tool_call_id") == call_id
    )


def _surface(tmp_path, *, audit=None):
    registry = _granted(HARNESS_TOOL_NAMES, AUTONOMOUS_TOOL_NAMES, audit=audit)
    register_harness_tools(registry, tmp_path)
    register_autonomous_tools(registry, tmp_path)
    return registry


def _entries(registry, *, global_):
    return json.loads(registry.dispatch("harness_list", {"global_": global_}))


# --- harness: ``global_`` is the only scope input -------------------------------


@pytest.mark.parametrize("scope", ["global", "local", "nonsense"])
def test_harness_upsert_scope_key_is_unknown_field_and_writes_nothing(tmp_path, scope):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch("harness_upsert", {**_ENTRY, "scope": scope}))

    assert result["code"] == "unknown_field"
    assert result["error"]
    assert _entries(registry, global_=False) == []
    assert _entries(registry, global_=True) == []


def test_harness_scope_key_cannot_override_the_global_flag(tmp_path):
    registry = _surface(tmp_path)

    result = json.loads(
        registry.dispatch(
            "harness_upsert", {**_ENTRY, "global_": False, "scope": "global"}
        )
    )

    assert result["code"] == "unknown_field"
    assert _entries(registry, global_=True) == []
    assert _entries(registry, global_=False) == []


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("harness_get", {"kind": "memory", "id": "note-1", "scope": "global"}),
        ("harness_list", {"scope": "global"}),
        ("harness_delete", {"kind": "memory", "id": "note-1", "scope": "global"}),
        (
            "harness_refine",
            {"trigger": "t", "proposals": [], "trajectory": "x", "scope": "global"},
        ),
        ("harness_rollback", {"scope": "global"}),
    ],
)
def test_every_harness_tool_rejects_a_scope_key(tmp_path, tool, arguments):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch(tool, arguments))

    assert result["code"] == "unknown_field"


def test_harness_global_flag_true_writes_only_the_global_store(tmp_path):
    registry = _surface(tmp_path)

    written = json.loads(
        registry.dispatch("harness_upsert", {**_ENTRY, "global_": True})
    )

    assert written["id"] == "note-1"
    assert [e["id"] for e in _entries(registry, global_=True)] == ["note-1"]
    assert _entries(registry, global_=False) == []


@pytest.mark.parametrize("flag", ["yes", 1, "true", None, []])
def test_harness_non_bool_global_flag_is_bad_type_and_writes_nothing(tmp_path, flag):
    registry = _surface(tmp_path)

    result = json.loads(
        registry.dispatch("harness_upsert", {**_ENTRY, "global_": flag})
    )

    assert result["code"] == "bad_type"
    assert _entries(registry, global_=False) == []
    assert _entries(registry, global_=True) == []


# --- omitted required fields reach the typed decoders ---------------------------


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("harness_upsert", {"kind": "memory", "title": "t", "body": "b"}),
        ("harness_upsert", {"kind": "memory", "id": "i", "body": "b"}),
        ("harness_upsert", {"kind": "memory", "id": "i", "title": "t"}),
        ("harness_get", {"kind": "memory"}),
        ("harness_delete", {"kind": "memory"}),
        ("harness_refine", {"trigger": "t", "trajectory": "x"}),
        ("harness_refine", {"proposals": [], "trajectory": "x"}),
        ("harness_refine", {"trigger": "t", "proposals": []}),
    ],
)
def test_harness_omitted_required_field_is_typed_bad_type(tmp_path, tool, arguments):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch(tool, arguments))

    assert result["code"] == "bad_type"
    assert result["error"].startswith("bad_type")


# --- typed failures are audited as errors, not allowed --------------------------


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("harness_upsert", {**_ENTRY, "scope": "global"}),
        ("harness_upsert", {**_ENTRY, "global_": "yes"}),
        ("harness_get", {"kind": "memory"}),
        ("autonomous_start", {"max_turns": True}),
        ("autonomous_start", {"bogus": 1}),
        ("autonomous_status", {"bogus": 1}),
        ("autonomous_stop", {"schema_version": 0}),
    ],
)
def test_typed_failure_is_audited_as_error(tmp_path, tool, arguments):
    audit = AuditLog(tmp_path / "audit" / "tools.ndjson")
    registry = _surface(tmp_path, audit=audit)

    result = json.loads(registry.dispatch(tool, arguments))

    assert "code" in result
    assert [(r["tool"], r["verdict"]) for r in audit.records()] == [(tool, "error")]


# --- autonomous: a non-finite time budget never starts a run --------------------


@pytest.mark.parametrize(
    "raw",
    [
        '{"max_minutes": NaN}',
        '{"max_minutes": Infinity}',
        '{"max_minutes": -Infinity}',
    ],
)
def test_autonomous_start_rejects_non_finite_max_minutes(tmp_path, raw):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch("autonomous_start", raw))

    assert result["code"] == "bad_value"
    assert result["error"].startswith("bad_value")
    assert json.loads(registry.dispatch("autonomous_status", {})) == _IDLE


def test_autonomous_start_rejects_non_finite_max_minutes_from_config(tmp_path):
    registry = _granted(AUTONOMOUS_TOOL_NAMES)
    register_autonomous_tools(registry, tmp_path, config={"max_minutes": float("inf")})

    result = json.loads(registry.dispatch("autonomous_start", {"max_turns": 3}))

    assert result["code"] == "bad_value"
    assert json.loads(registry.dispatch("autonomous_status", {})) == _IDLE


@pytest.mark.parametrize("raw", ['{"max_minutes": 5.5}', '{"max_minutes": 2}'])
def test_autonomous_start_accepts_a_finite_max_minutes(tmp_path, raw):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch("autonomous_start", raw))

    assert result["started"] is True
    assert result["budget"]["max_minutes"] == json.loads(raw)["max_minutes"]
    status = json.loads(registry.dispatch("autonomous_status", {}))
    assert status["running"] is True


def test_autonomous_start_rejects_an_undeclared_argument(tmp_path):
    registry = _surface(tmp_path)

    result = json.loads(registry.dispatch("autonomous_start", {"max_turns": 2, "x": 1}))

    assert result["code"] == "unknown_field"
    assert json.loads(registry.dispatch("autonomous_status", {})) == _IDLE


# --- the loop sees the same typed errors ----------------------------------------


def test_loop_scope_alias_is_a_typed_error_and_stores_stay_empty(tmp_path):
    registry = _surface(tmp_path)

    agent, result = _run(
        registry,
        [
            _tool_call(
                "harness_upsert",
                json.dumps({**_ENTRY, "scope": "global"}),
                "c1",
            ),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    row = _tool_row(agent, "c1")
    assert row.startswith("error:")
    assert "unknown_field" in row
    assert _entries(registry, global_=True) == []
    assert _entries(registry, global_=False) == []


def test_loop_non_finite_budget_is_typed_error_and_starts_no_run(tmp_path):
    registry = _surface(tmp_path)

    agent, result = _run(
        registry,
        [
            _tool_call("autonomous_start", '{"max_minutes": NaN}', "c1"),
            _tool_call("autonomous_status", "{}", "c2"),
            _tool_call("autonomous_start", '{"max_minutes": Infinity}', "c3"),
            _tool_call("autonomous_status", "{}", "c4"),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    for call_id in ("c1", "c3"):
        row = _tool_row(agent, call_id)
        assert row.startswith("error:")
        assert "bad_value" in row
    assert _model_tool_payload(agent, "c2") == _IDLE
    assert _model_tool_payload(agent, "c4") == _IDLE

    started = json.loads(registry.dispatch("autonomous_start", '{"max_minutes": 10}'))
    assert started["started"] is True
    assert started["budget"]["max_minutes"] == 10
    stopped = json.loads(registry.dispatch("autonomous_stop", {}))
    assert stopped["was_running"] is True


def test_loop_omitted_required_harness_field_is_typed_bad_type(tmp_path):
    registry = _surface(tmp_path)

    agent, result = _run(
        registry,
        [
            _tool_call(
                "harness_upsert",
                '{"kind": "memory", "title": "t", "body": "b"}',
                "c1",
            ),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    row = _tool_row(agent, "c1")
    assert row.startswith("error:")
    assert "bad_type" in row
    assert _entries(registry, global_=False) == []
