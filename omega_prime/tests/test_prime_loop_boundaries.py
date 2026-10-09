# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Loop boundaries through the real consuming path (CR-02, WR-12).

Every case runs the actual ``OmegaPrimeAgent.run`` with a scripted model against
the real goals tool family. Approval comes from real ``ApprovalLog`` grants by a
named human reviewer. State is read back from the persisted goal store, not from
the transcript alone.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from omega_prime.agent.goals import PrimeGoalStore
from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.goals import GOAL_TOOL_NAMES, register_goal_tools
from omega_prime.tools.registry import ToolRegistry

_OBJECTIVE = "Ship it"


class _UsageModel(ScriptedModel):
    """Scripted replies with per-call provider usage (dict or None)."""

    def __init__(self, script: list[dict], usages: list[Any]) -> None:
        super().__init__(script)
        self._usages = list(usages)
        self.last_usage: Any = None

    def complete(self, messages: list, tools: Any = None) -> dict:
        message = super().complete(messages, tools)
        self.last_usage = self._usages.pop(0) if self._usages else None
        return message


def _granted(*names: str) -> ToolRegistry:
    """A registry whose listed tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for name in names:
        receipt = log.approve(name, "phase61-human-reviewer")
        assert receipt["approved"] is True
    return ToolRegistry(approval_log=log)


def _goals_registry(root: Any, *granted: str) -> ToolRegistry:
    registry = _granted(*granted)
    register_goal_tools(registry, root)
    return registry


def _set_goal(registry: ToolRegistry) -> None:
    out = json.loads(
        registry.dispatch(
            "goal_set",
            {"objective": _OBJECTIVE, "token_budget": 10, "steps": ["one", "two"]},
        )
    )
    assert out["prime_status"] == "active"


def _tool_call(name: str, arguments: Any = "{}", call_id: str = "call-1") -> dict:
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


def _tool_round(*calls: tuple[str, Any, str]) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
            for name, arguments, call_id in calls
        ],
    }


def _final(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _run(registry: ToolRegistry, model: ScriptedModel) -> dict:
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=8
    )
    return agent.run("go")


def _tool_rows(result: dict) -> list[dict]:
    return [row for row in result["messages"] if row.get("role") == "tool"]


def _persisted(root: Any) -> dict:
    return PrimeGoalStore(root / "goals").prime_status()


# The goal's 10-token budget is exhausted by the final answer's usage, so the
# turn ends there instead of continuing into further scripted-model calls.
_USAGES = [None, None, {"total_tokens": 50}]


# --- CR-02: malformed arguments never reach the tool ----------------------------


def test_truncated_arguments_do_not_run_the_approved_write_tool(tmp_path):
    registry = _goals_registry(tmp_path, *GOAL_TOOL_NAMES)
    _set_goal(registry)
    model = _UsageModel(
        [
            _tool_call("goal_clear", '{"schema_version": 1'),
            _tool_call("goal_status", "", "call-2"),
            _final("done"),
        ],
        _USAGES,
    )
    result = _run(registry, model)

    rows = _tool_rows(result)
    assert [row["tool_call_id"] for row in rows] == ["call-1", "call-2"]
    assert rows[0]["name"] == "goal_clear"
    assert rows[0]["content"].startswith("error:")
    status = json.loads(rows[1]["content"])
    assert status["objective"] == _OBJECTIVE
    assert status["prime_status"] == "active"
    persisted = _persisted(tmp_path)
    assert persisted["objective"] == _OBJECTIVE
    assert persisted["prime_status"] != "cleared"
    assert model.call_count == 3
    assert result["final_response"] == "done"


@pytest.mark.parametrize(
    "arguments",
    ["[]", '"x"', "5", "null", "true", "[1, 2]", [], 7, 1.5, True],
    ids=[
        "json-list",
        "json-string",
        "json-number",
        "json-null",
        "json-bool",
        "json-list-items",
        "raw-list",
        "raw-int",
        "raw-float",
        "raw-bool",
    ],
)
def test_non_object_arguments_do_not_run_the_approved_write_tool(tmp_path, arguments):
    registry = _goals_registry(tmp_path, *GOAL_TOOL_NAMES)
    _set_goal(registry)
    model = _UsageModel(
        [
            _tool_call("goal_clear", arguments),
            _tool_call("goal_status", "", "call-2"),
            _final("done"),
        ],
        _USAGES,
    )
    result = _run(registry, model)

    rows = _tool_rows(result)
    assert len(rows) == 2
    assert rows[0]["content"].startswith("error:")
    status = json.loads(rows[1]["content"])
    assert status["objective"] == _OBJECTIVE
    assert status["prime_status"] == "active"
    persisted = _persisted(tmp_path)
    assert persisted["objective"] == _OBJECTIVE
    assert persisted["prime_status"] != "cleared"
    assert result["final_response"] == "done"


def test_malformed_call_fails_alone_within_a_round(tmp_path):
    registry = _goals_registry(tmp_path, *GOAL_TOOL_NAMES)
    _set_goal(registry)
    model = _UsageModel(
        [
            _tool_round(
                ("goal_clear", '{"global_": true', "call-a"),
                ("goal_status", "{}", "call-b"),
            ),
            _final("done"),
        ],
        [None, {"total_tokens": 50}],
    )
    result = _run(registry, model)

    rows = _tool_rows(result)
    assert [(row["name"], row["tool_call_id"]) for row in rows] == [
        ("goal_clear", "call-a"),
        ("goal_status", "call-b"),
    ]
    assert rows[0]["content"].startswith("error:")
    assert not rows[1]["content"].startswith("error:")
    status = json.loads(rows[1]["content"])
    assert status["objective"] == _OBJECTIVE
    assert status["prime_status"] == "active"
    persisted = _persisted(tmp_path)
    assert persisted["objective"] == _OBJECTIVE
    assert persisted["prime_status"] != "cleared"
    assert result["final_response"] == "done"


# --- WR-12: only the most recent tool round decides a refusal -------------------


def test_recovered_refusal_is_terminal_only_in_the_final_round(tmp_path):
    # goal_clear carries no grant, so its dispatch is a real approval refusal.
    recovered_root = tmp_path / "recovered"
    registry = _goals_registry(recovered_root, "goal_set", "goal_status")
    recovered = _run(
        registry,
        ScriptedModel(
            [
                _tool_call("goal_clear", "{}", "call-1"),
                _tool_call("goal_status", "{}", "call-2"),
                _final("recovered"),
            ]
        ),
    )
    rows = _tool_rows(recovered)
    assert rows[0]["content"].startswith("error:")
    assert not rows[1]["content"].startswith("error:")
    assert recovered["final_response"] == "recovered"
    assert recovered["completed"] is True
    assert recovered["turn_exit_reason"] != "approval_refused"

    final_root = tmp_path / "final"
    registry = _goals_registry(final_root, "goal_set", "goal_status")
    refused = _run(
        registry,
        ScriptedModel([_tool_call("goal_clear", "{}", "call-1"), _final("steady")]),
    )
    assert _tool_rows(refused)[0]["content"].startswith("error:")
    assert refused["final_response"] == "steady"
    assert refused["completed"] is False
    assert refused["turn_exit_reason"] == "approval_refused"
