# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over agent-to-agent messaging (CONN-01).

Sits between the ``agent_message_*`` tool handlers and
``omega_prime/agent/messaging.py`` (``SessionRegistry``). The message shape
is the verbatim Prime field set; a missing recipient stays a structured
error, never a silent drop (LOOP-04).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from omega_prime.agent.messaging import AgentMessage, SessionRegistry
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    optional_bool,
    reject_unknown,
    require_bool,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_SEND_FIELDS = frozenset({"schema_version", "sender", "recipient", "body"})
_OBSERVE_FIELDS = frozenset({"schema_version", "session", "mark_read"})


@dataclass(frozen=True)
class SendRequest:
    sender: str
    recipient: str
    body: str

    @classmethod
    def from_dict(cls, raw: Any) -> SendRequest:
        payload = require_payload(raw, what="SendRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="SendRequest")
        reject_unknown(payload, _SEND_FIELDS, what="SendRequest")
        return cls(
            sender=require_str(payload, "sender", what="SendRequest"),
            recipient=require_str(payload, "recipient", what="SendRequest"),
            body=require_str(payload, "body", what="SendRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ObserveRequest:
    session: str
    mark_read: bool = True

    @classmethod
    def from_dict(cls, raw: Any) -> ObserveRequest:
        payload = require_payload(raw, what="ObserveRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ObserveRequest")
        reject_unknown(payload, _OBSERVE_FIELDS, what="ObserveRequest")
        return cls(
            session=require_str(payload, "session", what="ObserveRequest"),
            mark_read=optional_bool(
                payload, "mark_read", what="ObserveRequest", default=True
            ),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class MessageView:
    """The JSON-safe view of one ``AgentMessage`` (verbatim Prime fields)."""

    id: str
    sender: str
    recipient: str
    body: str
    at: str
    read: bool = False

    @classmethod
    def from_message(cls, message: AgentMessage) -> MessageView:
        return cls(
            id=message.id,
            sender=message.sender,
            recipient=message.recipient,
            body=message.body,
            at=message.at,
            read=message.read,
        )

    @classmethod
    def from_dict(cls, raw: Any) -> MessageView:
        payload = require_payload(raw, what="MessageView")
        return cls(
            id=require_str(payload, "id", what="MessageView"),
            sender=require_str(payload, "sender", what="MessageView"),
            recipient=require_str(payload, "recipient", what="MessageView"),
            body=require_str(payload, "body", what="MessageView"),
            at=require_str(payload, "at", what="MessageView"),
            read=require_bool(payload, "read", what="MessageView"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class MessagingConnector:
    """The typed boundary over a shared ``SessionRegistry``."""

    def __init__(self, registry: SessionRegistry) -> None:
        self._registry = registry

    def send(self, request: SendRequest) -> dict:
        # Classified by cause, in the registry's own validation order (body,
        # sender, recipient), never by matching its message text: an invalid
        # body is decided from the input itself; of the two membership
        # failures only an unknown recipient carries the ``members`` hint.
        if not request.body:
            raise PrimeError("bad_value", "message body must be a non-empty string")
        out = self._registry.send(request.sender, request.recipient, request.body)
        if "error" in out:
            members = out.get("members")
            if members is None:
                raise PrimeError("unknown_sender", out["error"])
            raise PrimeError(
                "unknown_recipient", f"{out['error']} (members: {', '.join(members)})"
            )
        return {"delivered": out["delivered"]}

    def observe(self, request: ObserveRequest) -> dict:
        messages = self._registry.observe(request.session, mark_read=request.mark_read)
        if messages and "error" in messages[0]:
            raise PrimeError("unknown_session", messages[0]["error"])
        return {"messages": [MessageView.from_dict(m).to_dict() for m in messages]}

    def members(self) -> dict:
        return {"members": self._registry.members()}


__all__ = [
    "SCHEMA_VERSION",
    "MessageView",
    "MessagingConnector",
    "ObserveRequest",
    "SendRequest",
]
