"""Tests for agent-to-agent messaging (Phase 57). Hermetic: in-process."""

from __future__ import annotations

import pytest

from omega_prime.agent.messaging import SessionRegistry


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
    import json as _json

    from omega_prime.tools.agent_message import (
        MESSAGING_TOOL_NAMES,
        register_messaging_tools,
    )
    from omega_prime.tools.registry import ToolRegistry

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

    out = _json.loads(
        reg_a.dispatch("agent_message_send", {"recipient": "sess-b", "body": "ping"})
    )
    assert "delivered" in out
    inbox = _json.loads(reg_b.dispatch("agent_observe", {}))
    assert inbox[0]["body"] == "ping"
    assert inbox[0]["sender"] == "sess-a"


def test_messaging_send_requires_approval(tmp_path):
    from omega_prime.tools.agent_message import register_messaging_tools
    from omega_prime.tools.registry import ToolRegistry

    registry = ToolRegistry()
    register_messaging_tools(registry, "s", session_registry=SessionRegistry())
    assert registry.approval_required("agent_message_send") is True
    assert registry.approval_required("agent_observe") is False


def test_messaging_tools_disabled(tmp_path):
    from omega_prime.tools.agent_message import register_messaging_tools
    from omega_prime.tools.registry import ToolRegistry

    registry = ToolRegistry()
    assert register_messaging_tools(registry, "s", enabled=False) == []
    assert registry.schemas() == []
