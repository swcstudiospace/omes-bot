# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the agent-messaging tool family on one registry.

Ported from Prime Agent's agent messaging (see
``omega_prime/agent/messaging.py``). Gated on the ``prime.messaging.enabled``
config flag (default off); when disabled the family is absent from the registry
and roster (LOOP-05). The session registry is shared per ``root`` so two
sessions exchange messages through the rostered tools (LOOP-04).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from omega_prime.agent.messaging import SessionRegistry
from omega_prime.prime.messaging import MessagingConnector, ObserveRequest, SendRequest
from omega_prime.prime.types import reject_extra
from omega_prime.tools.registry import ToolRegistry

# Offered after the autonomous tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
MESSAGING_TOOL_NAMES = (
    "agent_message_send",
    "agent_observe",
)

_WRITE_TOOLS = frozenset({"agent_message_send"})

# One registry per process: Omega Prime is single-process, so the in-process
# registry is the truth (Prime's roster join collapses).
_SHARED: SessionRegistry | None = None


def _shared_registry() -> SessionRegistry:
    global _SHARED
    if _SHARED is None:
        _SHARED = SessionRegistry()
    return _SHARED


def register_messaging_tools(
    registry: ToolRegistry,
    session: str,
    *,
    enabled: bool = True,
    session_registry: SessionRegistry | None = None,
) -> list[str]:
    """Register the messaging family for one session.

    ``session`` is this agent's session name (registered on first use).
    ``enabled=False`` registers nothing (LOOP-05).
    """
    if not enabled:
        return []

    sessions = session_registry if session_registry is not None else _shared_registry()
    sessions.register(session)
    connector = MessagingConnector(sessions)

    # Both handlers decode through the typed/versioned request boundary
    # before touching the session registry (CONN-01). The sender / session is
    # this session's bound name and never a model-supplied field: any
    # undeclared argument is rejected, never merged into the payload.
    # Result envelopes are unchanged.

    def agent_message_send(
        recipient: Any = None,
        body: Any = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="agent_message_send")
        request = SendRequest.from_dict(
            {
                "sender": session,
                "recipient": recipient,
                "body": body,
                "schema_version": schema_version,
            }
        )
        return connector.send(request)

    def agent_observe(schema_version: int | None = None, **extra: Any) -> list:
        reject_extra(extra, what="agent_observe")
        request = ObserveRequest.from_dict(
            {"session": session, "schema_version": schema_version}
        )
        return connector.observe(request)["messages"]

    handlers: dict[str, Callable[..., Any]] = {
        "agent_message_send": agent_message_send,
        "agent_observe": agent_observe,
    }
    if tuple(handlers) != MESSAGING_TOOL_NAMES:
        raise RuntimeError("messaging tool handlers drifted from MESSAGING_TOOL_NAMES")
    for name in MESSAGING_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(MESSAGING_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "agent_message_send": (
        "Send a message to another registered session. A missing recipient is a "
        "structured error, never a silent drop.",
        _object(
            {
                "recipient": _string("The recipient session name."),
                "body": _string("The message body."),
            },
            ["recipient", "body"],
        ),
    ),
    "agent_observe": (
        "Read this session's inbox (marks messages read).",
        _object({}, []),
    ),
}

__all__ = ["MESSAGING_TOOL_NAMES", "register_messaging_tools"]
