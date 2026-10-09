# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Registered goal tool surface: strict decoding, atomic replace, no stale steps.

Every case drives ``goal_set`` through ``registry.dispatch`` with real human
grants, or through the real ``OmegaPrimeAgent.run`` with a scripted model for
what the model and the continuation loop observe. Goal files live under
``tmp_path``.
"""

from __future__ import annotations

import json

from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.audit.log import AuditLog
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.goals import GOAL_TOOL_NAMES, register_goal_tools
from omega_prime.tools.registry import ToolRegistry

_NO_FILES = {"goals.json": None, "prime_goal.json": None}


class _UsageModel(ScriptedModel):
    """Scripted replies that each report provider usage."""

    def __init__(self, script):
        super().__init__(script)
        self.last_usage = None

    def complete(self, messages, tools=None):
        message = super().complete(messages, tools)
        self.last_usage = {"total_tokens": 3}
        return message


def _granted(*families):
    """A registry whose tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for family in families:
        for name in family:
            receipt = log.approve(name, "phase61-human-reviewer")
            assert receipt["approved"] is True
    return ToolRegistry(approval_log=log)


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


def _registry(tmp_path):
    registry = _granted(GOAL_TOOL_NAMES)
    register_goal_tools(registry, tmp_path)
    return registry


def _goal_files(tmp_path):
    goals = tmp_path / "goals"
    return {
        name: (goals / name).read_bytes() if (goals / name).exists() else None
        for name in ("goals.json", "prime_goal.json")
    }


def _goal_set(registry, **arguments):
    return json.loads(registry.dispatch("goal_set", arguments))


def test_blank_step_is_rejected_and_the_stored_goal_is_untouched(tmp_path):
    registry = _registry(tmp_path)
    seeded = _goal_set(registry, objective="Keep me", steps=["keep-1"])
    assert seeded["prime_status"] == "active"
    before = _goal_files(tmp_path)

    bad = _goal_set(registry, objective="Replace me", steps=["fine", "   "])

    assert bad["code"] == "bad_value"
    assert _goal_files(tmp_path) == before
    status = json.loads(registry.dispatch("goal_status", {}))
    assert status["objective"] == "Keep me"
    assert [step["text"] for step in status["steps"]] == ["keep-1"]


def test_blank_step_on_a_fresh_store_writes_nothing(tmp_path):
    registry = _registry(tmp_path)

    bad = _goal_set(registry, objective="Never stored", steps=["ok", ""])

    assert bad["code"] == "bad_value"
    assert _goal_files(tmp_path) == _NO_FILES
    status = json.loads(registry.dispatch("goal_status", {}))
    assert status["prime_status"] == "cleared"


def test_blank_objective_is_rejected_and_the_stored_goal_is_untouched(tmp_path):
    registry = _registry(tmp_path)
    _goal_set(registry, objective="Keep me", steps=["keep-1"])
    before = _goal_files(tmp_path)

    bad = _goal_set(registry, objective="   ", steps=["x"])

    assert bad["code"] == "bad_value"
    assert _goal_files(tmp_path) == before
    status = json.loads(registry.dispatch("goal_status", {}))
    assert status["objective"] == "Keep me"
    assert [step["text"] for step in status["steps"]] == ["keep-1"]


def test_blank_objective_on_a_fresh_store_writes_nothing(tmp_path):
    registry = _registry(tmp_path)

    bad = _goal_set(registry, objective="   ", steps=["x"])

    assert bad["code"] == "bad_value"
    assert _goal_files(tmp_path) == _NO_FILES


def test_second_goal_set_replaces_steps_and_continues_on_the_new_ones(tmp_path):
    registry = _registry(tmp_path)
    _goal_set(registry, objective="First", steps=["old-1", "old-2"])

    replaced = _goal_set(registry, objective="Second", steps=["new-1", "new-2"])

    assert replaced["objective"] == "Second"
    assert [step["text"] for step in replaced["steps"]] == ["new-1", "new-2"]
    status = json.loads(registry.dispatch("goal_status", {}))
    assert [step["text"] for step in status["steps"]] == ["new-1", "new-2"]
    assert all(step["done"] is False for step in status["steps"])

    model = _UsageModel(
        [
            {"role": "assistant", "content": "part one"},
            {"role": "assistant", "content": "part two"},
        ]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=2
    )
    agent.run("go")

    continuation = model.seen[1][-1]
    assert continuation["role"] == "user"
    assert "new-1" in continuation["content"]
    assert "old-1" not in continuation["content"]
    assert "old-2" not in continuation["content"]


def test_goal_set_without_steps_defines_a_goal_with_no_steps(tmp_path):
    registry = _registry(tmp_path)
    _goal_set(registry, objective="First", steps=["old-1"])

    replaced = _goal_set(registry, objective="Second")

    assert replaced["steps"] == []
    status = json.loads(registry.dispatch("goal_status", {}))
    assert status["objective"] == "Second"
    assert status["steps"] == []


def test_stale_after_turns_is_not_a_tool_argument(tmp_path):
    registry = _registry(tmp_path)
    _goal_set(registry, objective="Keep me", steps=["keep-1"])
    before = _goal_files(tmp_path)

    bad = _goal_set(registry, objective="Other", stale_after_turns=1)

    assert bad["code"] == "unknown_field"
    assert _goal_files(tmp_path) == before


def test_stale_after_turns_on_a_fresh_store_writes_nothing(tmp_path):
    registry = _registry(tmp_path)

    bad = _goal_set(registry, objective="Never stored", stale_after_turns=1)

    assert bad["code"] == "unknown_field"
    assert _goal_files(tmp_path) == _NO_FILES


def test_omitted_objective_is_a_typed_error_not_a_python_type_error(tmp_path):
    registry = _registry(tmp_path)

    bad = _goal_set(registry)

    assert bad["code"] == "bad_type"
    assert _goal_files(tmp_path) == _NO_FILES


def test_model_calling_goal_set_without_objective_sees_the_typed_code(tmp_path):
    registry = _registry(tmp_path)
    model = ScriptedModel(
        [
            _tool_call("goal_set", "{}"),
            {"role": "assistant", "content": "noted"},
        ]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )

    result = agent.run("go")

    assert result["final_response"] == "noted"
    assert "bad_type" in json.dumps(agent.messages)
    assert _goal_files(tmp_path) == _NO_FILES


def test_rejected_goal_set_is_audited_as_an_error(tmp_path):
    approvals = ApprovalLog()
    receipt = approvals.approve("goal_set", "phase61-human-reviewer")
    assert receipt["approved"] is True
    audit = AuditLog(tmp_path / "audit.ndjson")
    registry = ToolRegistry(approval_log=approvals, audit=audit)
    register_goal_tools(registry, tmp_path)

    bad = _goal_set(registry, objective="Other", schema_version=99)

    assert bad["code"] == "unsupported_schema_version"
    assert [(r["tool"], r["verdict"]) for r in audit.records()] == [
        ("goal_set", "error")
    ]
