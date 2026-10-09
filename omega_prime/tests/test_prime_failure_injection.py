"""Failure-injection tests through the actual consuming loop (CONN-03).

Every failure case runs the real ``OmegaPrimeAgent.run`` with a scripted
model against genuinely registered tools: a raising child runner, an
event-gated collect timeout, a malformed request, and a malformed stored
response. Each failure surfaces inside the model-visible transcript with
its structured code or real error text, no denied or malformed call
takes effect, and a subsequent valid turn recovers. Approval comes from
real ``ApprovalLog`` grants by a named human reviewer, never an
always-approve stand-in; child timing comes from ``threading.Event``
gates, never fixed sleeps or wall-clock polls.
"""

from __future__ import annotations

import json
import threading

from omega_prime.agent.messaging import SessionRegistry
from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.rlm import host_for
from omega_prime.agent.runtime import OmegaPrimeAgent
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
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.rlm import RLM_TOOL_NAMES, register_rlm_tools


class _Parent:
    """The host-side parent contract (session/depth/limit wiring)."""

    def __init__(self, tmp_path):
        self.delegate_depth = 0
        self.max_depth = 2
        self.max_children = 4
        self.session_dir = str(tmp_path)
        self.session_name = None


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


# --- raise: child crash settles into the loop, then recovery --------------------


def test_loop_child_crash_settles_then_recovers(tmp_path):
    calls = []

    def flaky(prompt, model=None, thinking=None):
        calls.append(prompt)
        if len(calls) == 1:
            raise RuntimeError("kernel panicked mid-child")
        return "steady answer"

    registry = _granted(RLM_TOOL_NAMES)
    register_rlm_tools(registry, _Parent(tmp_path), run_child=flaky)
    agent, result = _run(
        registry,
        [
            _tool_call("rlm_spawn", '{"prompt":"brittle","name":"kid1"}', "c1"),
            _tool_call("rlm_collect", '{"targets":["kid1"],"timeout_ms":5000}', "c2"),
            _tool_call("rlm_spawn", '{"prompt":"steady","name":"kid2"}', "c3"),
            _tool_call("rlm_collect", '{"targets":["kid2"],"timeout_ms":5000}', "c4"),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    assert result["final_response"] == "recovered"
    crashed = _model_tool_payload(agent, "c2")[0]
    assert crashed["status"] == "error"
    assert crashed["settled"] is True
    assert "kernel panicked mid-child" in crashed["error"]
    recovered = _model_tool_payload(agent, "c4")[0]
    assert recovered["status"] == "done"
    assert recovered["answer_preview"] == "steady answer"
    listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
    assert {r["session_name"] for r in listed} == {"kid1", "kid2"}


def test_loop_capability_raise_is_model_error_then_recovers(tmp_path):
    registry = _granted(RLM_TOOL_NAMES)
    register_rlm_tools(
        registry,
        _Parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: "ok",
    )
    agent, result = _run(
        registry,
        [
            _tool_call("rlm_delete_subagent", '{"target": "ghost"}', "c1"),
            _tool_call("rlm_spawn", '{"prompt":"work","name":"kid"}', "c2"),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    assert result["final_response"] == "recovered"
    transcript = json.dumps(agent.messages)
    assert "No direct RLM subagent matches" in transcript
    listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
    assert [r["session_name"] for r in listed] == ["kid"]


# --- timeout: event-gated snapshot, then recovery --------------------------------


def test_loop_collect_timeout_snapshot_then_recovers(tmp_path):
    gate = threading.Event()

    def gated(prompt, model=None, thinking=None):
        gate.wait(timeout=60)
        return "gated answer"

    registry = _granted(RLM_TOOL_NAMES)
    parent = _Parent(tmp_path)
    register_rlm_tools(registry, parent, run_child=gated)
    model = ScriptedModel(
        [
            _tool_call("rlm_spawn", '{"prompt":"slow","name":"kid"}', "c1"),
            _tool_call("rlm_collect", '{"timeout_ms": 50}', "c2"),
            {"role": "assistant", "content": "snapshot seen"},
            _tool_call("rlm_collect", '{"timeout_ms": 5000}', "c3"),
            {"role": "assistant", "content": "recovered"},
        ]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=6
    )

    try:
        first = agent.run("go")
        assert first["final_response"] == "snapshot seen"
        snapshot = _model_tool_payload(agent, "c2")[0]
        assert snapshot["status"] == "running"
        assert snapshot["settled"] is False

        gate.set()
        second = agent.run("again")
        assert second["final_response"] == "recovered"
        recovered = _model_tool_payload(agent, "c3")[0]
        assert recovered["status"] == "done"
        assert recovered["answer_preview"] == "gated answer"
    finally:
        gate.set()
        host_for(parent, True).shutdown()
        agent.close()


# --- malformed request: typed code in the loop, then recovery --------------------


def test_loop_malformed_spawn_reaches_model_typed_then_recovers(tmp_path):
    registry = _granted(RLM_TOOL_NAMES)
    register_rlm_tools(
        registry,
        _Parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: f"done: {prompt}",
    )
    agent, result = _run(
        registry,
        [
            _tool_call(
                "rlm_spawn",
                '{"prompt": "work", "name": "kid", "model": true}',
                "call-bad",
            ),
            _tool_call(
                "rlm_spawn",
                '{"prompt": "work", "name": "kid"}',
                "call-good",
            ),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    assert result["final_response"] == "recovered"
    # The typed code survived registry dispatch into the model transcript.
    assert "bad_type" in json.dumps(agent.messages)
    # The malformed call created nothing; exactly the valid child exists.
    listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
    assert [r["session_name"] for r in listed] == ["kid"]


# --- malformed response: corrupt stored status is typed, then recovery -----------


def test_loop_malformed_stored_status_is_typed_then_recovers(tmp_path):
    registry = _granted(GOAL_TOOL_NAMES)
    register_goal_tools(registry, tmp_path)
    json.loads(registry.dispatch("goal_set", {"objective": "x"}))

    sidecar = tmp_path / "goals" / "prime_goal.json"
    document = json.loads(sidecar.read_text())
    document["status"] = "teleported"
    sidecar.write_text(json.dumps(document))

    agent, result = _run(
        registry,
        [
            _tool_call("goal_status", "{}", "c1"),
            _tool_call("goal_clear", "{}", "c2"),
            _tool_call("goal_set", '{"objective": "fresh"}', "c3"),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    assert result["final_response"] == "recovered"
    assert "prime_status" in json.dumps(agent.messages)
    assert json.loads(registry.dispatch("goal_status", {}))["prime_status"] == "active"


# --- versioned input reaches the strict decoders ---------------------------------


def test_registered_versioned_inputs_reach_strict_decoders(tmp_path):
    registry = _granted(
        RLM_TOOL_NAMES,
        HARNESS_TOOL_NAMES,
        GOAL_TOOL_NAMES,
        AUTONOMOUS_TOOL_NAMES,
        MESSAGING_TOOL_NAMES,
    )
    register_rlm_tools(
        registry,
        _Parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: "ok",
    )
    register_harness_tools(registry, tmp_path)
    register_goal_tools(registry, tmp_path)
    register_autonomous_tools(registry, tmp_path)
    register_messaging_tools(registry, "a", session_registry=SessionRegistry())

    # An explicit current version is accepted everywhere.
    assert (
        json.loads(
            registry.dispatch(
                "rlm_spawn",
                {"prompt": "p", "name": "n", "schema_version": 1},
            )
        )["name"]
        == "n"
    )
    assert (
        json.loads(
            registry.dispatch(
                "harness_upsert",
                {
                    "kind": "memory",
                    "id": "i",
                    "title": "t",
                    "body": "b",
                    "schema_version": 1,
                },
            )
        )["id"]
        == "i"
    )
    assert (
        json.loads(
            registry.dispatch("goal_set", {"objective": "o", "schema_version": 1})
        )["prime_status"]
        == "active"
    )
    assert (
        json.loads(
            registry.dispatch("autonomous_start", {"max_turns": 1, "schema_version": 1})
        )["started"]
        is True
    )

    # An explicit future version is a strict typed error, with no effect.
    for tool, arguments in [
        ("rlm_spawn", {"prompt": "p", "name": "x", "schema_version": 999}),
        ("rlm_collect", {"schema_version": 999}),
        ("rlm_list_subagents", {"schema_version": 999}),
        ("goal_status", {"schema_version": 999}),
        ("harness_rollback", {"schema_version": 999}),
        ("autonomous_status", {"schema_version": 999}),
        ("agent_observe", {"schema_version": 999}),
        (
            "agent_message_send",
            {"recipient": "a", "body": "x", "schema_version": 999},
        ),
    ]:
        bad = json.loads(registry.dispatch(tool, arguments))
        assert bad["code"] == "unsupported_schema_version", tool

    # Unknown fields are strict typed errors, not generic TypeErrors.
    for tool, arguments in [
        ("rlm_spawn", {"prompt": "p", "name": "y", "surprise": 1}),
        ("rlm_list_subagents", {"bogus": 1}),
        ("goal_status", {"bogus": 1}),
        ("harness_list", {"bogus": 1}),
    ]:
        bad = json.loads(registry.dispatch(tool, arguments))
        assert bad["code"] == "unknown_field", tool
    listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
    assert {r["session_name"] for r in listed} == {"n"}


# --- malformed payloads across families, then recovery ---------------------------


def test_registered_harness_goals_autonomous_malformed_then_recover(tmp_path):
    registry = _granted(HARNESS_TOOL_NAMES, GOAL_TOOL_NAMES, AUTONOMOUS_TOOL_NAMES)
    register_harness_tools(registry, tmp_path)
    register_goal_tools(registry, tmp_path)
    register_autonomous_tools(registry, tmp_path)

    bad = json.loads(
        registry.dispatch(
            "harness_upsert",
            {"kind": "widget", "id": "i", "title": "t", "body": "b"},
        )
    )
    assert bad["code"] == "bad_value"
    bad = json.loads(
        registry.dispatch(
            "harness_upsert",
            {"kind": "memory", "id": "i", "title": "t", "body": "b", "global_": "yes"},
        )
    )
    assert bad["code"] == "bad_type"

    bad = json.loads(
        registry.dispatch("goal_set", {"objective": "o", "token_budget": True})
    )
    assert bad["code"] == "bad_type"
    bad = json.loads(
        registry.dispatch("goal_set", {"objective": "o", "steps": ["ok", 7]})
    )
    assert bad["code"] == "bad_type"
    assert json.loads(registry.dispatch("goal_status", {}))["prime_status"] == "cleared"

    bad = json.loads(registry.dispatch("autonomous_start", {"gate": "make test"}))
    assert bad["code"] == "bad_type"
    bad = json.loads(registry.dispatch("autonomous_start", {"max_turns": True}))
    assert bad["code"] == "bad_type"
    assert json.loads(registry.dispatch("autonomous_status", {})) == {
        "running": False,
        "stopped": None,
    }

    assert (
        json.loads(
            registry.dispatch(
                "harness_upsert",
                {"kind": "memory", "id": "i", "title": "t", "body": "b"},
            )
        )["id"]
        == "i"
    )
    assert (
        json.loads(registry.dispatch("goal_set", {"objective": "o"}))["prime_status"]
        == "active"
    )
    assert (
        json.loads(registry.dispatch("autonomous_start", {"max_turns": 2}))["started"]
        is True
    )


# --- denial: no side effect ------------------------------------------------------


def test_denied_tools_create_nothing_then_approved_recovers(tmp_path):
    denied = ToolRegistry()  # no approval log: write tools stay unapproved
    parent = _Parent(tmp_path)
    shared = SessionRegistry()
    register_rlm_tools(
        denied, parent, run_child=lambda prompt, model=None, thinking=None: "ok"
    )
    register_harness_tools(denied, tmp_path)
    register_goal_tools(denied, tmp_path)
    register_autonomous_tools(denied, tmp_path)
    register_messaging_tools(denied, "s", session_registry=shared)

    assert json.loads(denied.dispatch("rlm_spawn", {"prompt": "p", "name": "kid"})) == {
        "error": "approval required",
        "tool": "rlm_spawn",
    }
    assert json.loads(denied.dispatch("rlm_list_subagents", {})) == []
    assert json.loads(
        denied.dispatch(
            "harness_upsert", {"kind": "memory", "id": "i", "title": "t", "body": "b"}
        )
    ) == {"error": "approval required", "tool": "harness_upsert"}
    assert json.loads(denied.dispatch("goal_set", {"objective": "o"})) == {
        "error": "approval required",
        "tool": "goal_set",
    }
    assert json.loads(denied.dispatch("goal_status", {}))["prime_status"] == "cleared"
    assert json.loads(denied.dispatch("autonomous_start", {"max_turns": 1})) == {
        "error": "approval required",
        "tool": "autonomous_start",
    }

    # The same operations succeed under real grants.
    registry = _granted(RLM_TOOL_NAMES, GOAL_TOOL_NAMES)
    register_rlm_tools(
        registry,
        _Parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: "ok",
    )
    register_goal_tools(registry, tmp_path)
    assert (
        json.loads(registry.dispatch("rlm_spawn", {"prompt": "p", "name": "kid"}))[
            "name"
        ]
        == "kid"
    )
    assert (
        json.loads(registry.dispatch("goal_set", {"objective": "o"}))["prime_status"]
        == "active"
    )
