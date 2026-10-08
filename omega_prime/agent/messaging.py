# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Agent-to-agent messaging — a behavior port of Prime Agent's messaging.

Source contract: ``pa-daemon/src/agent_messaging*.rs`` @ ``967eb13f`` (MIT,
PrimeIntellect). Prime's roster join (parent / direct children / siblings)
collapses in Omega Prime: the agent is single-process, so an in-process
session registry is the truth. Delivery is direct; a missing recipient is a
structured error, never a silent drop (LOOP-04).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class AgentMessage:
    """One delivered message (verbatim Prime field names)."""

    id: str
    sender: str
    recipient: str
    body: str
    at: str
    read: bool = False


@dataclass
class _Session:
    name: str
    inbox: list[AgentMessage] = field(default_factory=list)


class SessionRegistry:
    """In-process registry of named sessions and their inboxes.

    The family view (parent / children / siblings) is the registry's
    membership: any registered session may message any other. A send to an
    unregistered recipient returns a structured error.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()

    def register(self, name: str) -> dict:
        """Register a session by name. Re-registering is idempotent."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("session name must be a non-empty string")
        with self._lock:
            self._sessions.setdefault(name, _Session(name=name))
        return {"registered": name}

    def unregister(self, name: str) -> dict:
        with self._lock:
            removed = self._sessions.pop(name, None)
        return {"unregistered": name, "existed": removed is not None}

    def members(self) -> list[str]:
        with self._lock:
            return sorted(self._sessions)

    def send(self, sender: str, recipient: str, body: str) -> dict:
        """Deliver ``body`` from ``sender`` to ``recipient``.

        Both endpoints must be registered. A missing recipient (or sender) is
        a structured error, never a silent drop.
        """
        if not isinstance(body, str) or not body:
            return {"error": "message body must be a non-empty string"}
        with self._lock:
            if sender not in self._sessions:
                return {"error": f"unknown sender session: {sender!r}"}
            target = self._sessions.get(recipient)
            if target is None:
                return {
                    "error": f"unknown recipient session: {recipient!r}",
                    "members": sorted(self._sessions),
                }
            message = AgentMessage(
                id=uuid.uuid4().hex,
                sender=sender,
                recipient=recipient,
                body=body,
                at=_now(),
            )
            target.inbox.append(message)
        return {"delivered": asdict(message)}

    def observe(self, name: str, *, mark_read: bool = True) -> list[dict]:
        """List a session's inbox. Unknown session is a structured error."""
        with self._lock:
            session = self._sessions.get(name)
            if session is None:
                return [
                    {
                        "error": f"unknown session: {name!r}",
                        "members": sorted(self._sessions),
                    }
                ]
            if mark_read:
                for message in session.inbox:
                    object.__setattr__(message, "read", True)
            messages = [asdict(m) for m in session.inbox]
        return messages


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


__all__ = ["AgentMessage", "SessionRegistry"]
