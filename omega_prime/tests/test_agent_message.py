"""Tests for agent-to-agent messaging (Phase 57). Hermetic: in-process."""

from __future__ import annotations

import json

import pytest

from omega_prime.agent.messaging import SessionRegistry
from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.messaging import MessagingConnector, ObserveRequest, SendRequest
from omega_prime.tools.agent_message import (
    MESSAGING_TOOL_NAMES,
    register_messaging_tools,
)
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.registry import ToolRegistry


def test_send_and_observe_between_sessions():
    registry = SessionRegistry()
    registry.register("alpha")
    registry.register("beta")
    out = registry.send("alpha", "beta", "hello beta")
    assert "delivered" in out
    inbox = registry.observe("beta")
    assert len(inbox) == 1
    assert inbox[0]["sender"] == "alpha"
    assert inbox[0]["body"] == "hello beta"
    assert inbox[0]["read"] is True


def test_missing_recipient_is_structured_error():
    registry = SessionRegistry()
    registry.register("alpha")
    out = registry.send("alpha", "ghost", "anyone?")
    assert "error" in out
    assert "ghost" in out["error"]
    assert out["members"] == ["alpha"]


def test_missing_sender_is_structured_error():
    registry = SessionRegistry()
    registry.register("beta")
    out = registry.send("ghost", "beta", "hi")
    assert "error" in out


def test_observe_unknown_session_is_error():
    registry = SessionRegistry()
    out = registry.observe("nope")
    assert "error" in out[0]


def test_empty_body_rejected():
    registry = SessionRegistry()
    registry.register("a")
    registry.register("b")
    assert "error" in registry.send("a", "b", "")


def test_register_validates_and_is_idempotent():
    registry = SessionRegistry()
    with pytest.raises(ValueError):
        registry.register("  ")
    registry.register("x")
    registry.register("x")
    assert registry.members() == ["x"]


def test_messaging_tools_exchange(tmp_path):
    class _Approvals:
        def is_approved(self, name):
            return True

    shared = SessionRegistry()
    reg_a = ToolRegistry(approval_log=_Approvals())
    reg_b = ToolRegistry(approval_log=_Approvals())
    assert register_messaging_tools(reg_a, "sess-a", session_registry=shared) == list(
        MESSAGING_TOOL_NAMES
    )
    register_messaging_tools(reg_b, "sess-b", session_registry=shared)

    out = json.loads(
        reg_a.dispatch("agent_message_send", {"recipient": "sess-b", "body": "ping"})
    )
    assert "delivered" in out
    inbox = json.loads(reg_b.dispatch("agent_observe", {}))
    assert inbox[0]["body"] == "ping"
    assert inbox[0]["sender"] == "sess-a"


def test_messaging_send_requires_approval(tmp_path):
    registry = ToolRegistry()
    register_messaging_tools(registry, "s", session_registry=SessionRegistry())
    assert registry.approval_required("agent_message_send") is True
    assert registry.approval_required("agent_observe") is False


def test_messaging_tools_disabled(tmp_path):
    registry = ToolRegistry()
    assert register_messaging_tools(registry, "s", enabled=False) == []
    assert registry.schemas() == []


# --- bound identity, typed errors and cause mapping (Phase 61 review) ------------


def _granted():
    """A registry whose messaging tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for name in MESSAGING_TOOL_NAMES:
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


def _tool_row(agent, call_id):
    return next(
        row
        for row in agent.provider_model.seen[-1]
        if row.get("role") == "tool" and row.get("tool_call_id") == call_id
    )


def _model_tool_payload(agent, call_id):
    """The decoded row of a SUCCESSFUL call (rejections render as plain text)."""
    return json.loads(_tool_row(agent, call_id)["content"])


def _alice_bob_carol():
    """alice is the bound session; bob and alice each hold an unread note."""
    sessions = SessionRegistry()
    registry = _granted()
    register_messaging_tools(registry, "alice", session_registry=sessions)
    sessions.register("bob")
    sessions.register("carol")
    assert "delivered" in sessions.send("carol", "bob", "secret-for-bob")
    assert "delivered" in sessions.send("carol", "alice", "note-for-alice")
    return sessions, registry


def test_loop_observe_cannot_read_another_session_inbox():
    sessions, registry = _alice_bob_carol()
    agent, result = _run(
        registry,
        [
            _tool_call("agent_observe", '{"session": "bob"}', "c1"),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    content = _tool_row(agent, "c1")["content"]
    assert content.startswith("error:")
    assert "unknown_field" in content
    assert "secret-for-bob" not in content
    assert [m["read"] for m in sessions.observe("bob", mark_read=False)] == [False]


def test_loop_send_cannot_forge_the_sender():
    sessions, registry = _alice_bob_carol()
    agent, result = _run(
        registry,
        [
            _tool_call(
                "agent_message_send",
                '{"sender": "carol", "recipient": "bob", "body": "forged"}',
                "c1",
            ),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    content = _tool_row(agent, "c1")["content"]
    assert content.startswith("error:")
    assert "unknown_field" in content
    assert [m["body"] for m in sessions.observe("bob", mark_read=False)] == [
        "secret-for-bob"
    ]


def test_loop_observe_rejects_undeclared_mark_read_and_leaves_inbox_unread():
    sessions, registry = _alice_bob_carol()
    agent, _ = _run(
        registry,
        [
            _tool_call("agent_observe", '{"mark_read": false}', "c1"),
            {"role": "assistant", "content": "done"},
        ],
    )

    content = _tool_row(agent, "c1")["content"]
    assert content.startswith("error:")
    assert "unknown_field" in content
    assert [m["read"] for m in sessions.observe("alice", mark_read=False)] == [False]


def test_loop_valid_send_and_observe_use_the_bound_identity():
    sessions, registry = _alice_bob_carol()
    agent, result = _run(
        registry,
        [
            _tool_call(
                "agent_message_send",
                '{"recipient": "bob", "body": "hello bob"}',
                "c1",
            ),
            _tool_call("agent_observe", "{}", "c2"),
            {"role": "assistant", "content": "done"},
        ],
    )

    assert result["final_response"] == "done"
    assert "delivered" in _model_tool_payload(agent, "c1")
    own = _model_tool_payload(agent, "c2")
    assert [m["body"] for m in own] == ["note-for-alice"]
    inbox = sessions.observe("bob", mark_read=False)
    assert [(m["sender"], m["body"]) for m in inbox] == [
        ("carol", "secret-for-bob"),
        ("alice", "hello bob"),
    ]


def test_omitted_recipient_is_a_typed_bad_type_error():
    sessions, registry = _alice_bob_carol()
    out = json.loads(registry.dispatch("agent_message_send", {"body": "orphan"}))

    assert out["error"].startswith("bad_type")
    assert out["code"] == "bad_type"
    assert [m["body"] for m in sessions.observe("bob", mark_read=False)] == [
        "secret-for-bob"
    ]


def test_connector_maps_each_failure_cause_to_its_own_code():
    sessions = SessionRegistry()
    sessions.register("alice")
    sessions.register("bob")
    connector = MessagingConnector(sessions)

    def code_of(call) -> str:
        with pytest.raises(PrimeError) as caught:
            call()
        return caught.value.code

    assert (
        code_of(lambda: connector.send(SendRequest("alice", "ghost", "hi")))
        == "unknown_recipient"
    )
    assert (
        code_of(lambda: connector.send(SendRequest("ghost", "bob", "hi")))
        == "unknown_sender"
    )
    assert (
        code_of(lambda: connector.send(SendRequest("alice", "bob", ""))) == "bad_value"
    )
    assert (
        code_of(lambda: connector.observe(ObserveRequest("ghost"))) == "unknown_session"
    )
    assert sessions.observe("bob", mark_read=False) == []
