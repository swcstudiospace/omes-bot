"""In-process approval log for gated tools.

Adapted from Hermes ``tools/approval.py`` ``approve_session``. This log records
a tool name, who approved it, when, and optionally when the approval expires. It
has no gateway queue and no prompt. The bot cannot approve its own tool. An
approval with a TTL stops counting once the injected clock passes ``expires_at``;
an approval without a TTL lasts until ``revoke`` or process exit. The log is
thread-safe and holds no event-loop state; it is not persisted.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from typing import Any


class ApprovalLog:
    """Names a person has approved. A refused ``approve`` records nothing."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._approved: dict[str, dict[str, Any]] = {}

    def approve(
        self,
        tool_name: str,
        approved_by: str,
        *,
        bot_id: str = "bot-00-omega-prime",
        ttl_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Record ``tool_name`` when ``approved_by`` is a person, not ``bot_id``.

        ``ttl_seconds`` (finite, > 0) makes the approval expire; the result then
        carries ``expires_at`` in epoch seconds. Re-approving replaces the entry.
        """
        if not isinstance(tool_name, str) or tool_name == "":
            return {"approved": False, "error": "tool name must be a non-empty string"}
        if not isinstance(approved_by, str) or approved_by.strip() == "":
            return {
                "approved": False,
                "error": "approved_by must be a non-empty string",
            }
        if not isinstance(bot_id, str) or bot_id == "":
            return {"approved": False, "error": "bot_id must be a non-empty string"}
        if approved_by == bot_id:
            return {"approved": False, "error": "approved_by must not be the bot"}
        if ttl_seconds is not None and (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, (int, float))
            or not math.isfinite(ttl_seconds)
            or ttl_seconds <= 0
        ):
            return {
                "approved": False,
                "error": "ttl_seconds must be a finite number greater than 0",
            }
        now = float(self._clock())
        expires_at = None if ttl_seconds is None else now + float(ttl_seconds)
        with self._lock:
            self._approved[tool_name] = {
                "tool": tool_name,
                "approved_by": approved_by,
                "approved_at": now,
                "expires_at": expires_at,
            }
        result: dict[str, Any] = {
            "approved": True,
            "tool": tool_name,
            "approved_by": approved_by,
            "bot_id": bot_id,
        }
        if expires_at is not None:
            result["expires_at"] = expires_at
        return result

    def revoke(self, tool_name: str) -> bool:
        """Forget an approval. True when an unexpired approval was removed."""
        if not isinstance(tool_name, str):
            return False
        now = float(self._clock())
        with self._lock:
            entry = self._approved.pop(tool_name, None)
        return entry is not None and not _expired(entry, now)

    def entries(self) -> list[dict[str, Any]]:
        """Live approvals sorted by tool name; expired entries are dropped."""
        now = float(self._clock())
        with self._lock:
            self._purge(now)
            return [dict(self._approved[name]) for name in sorted(self._approved)]

    def is_approved(self, tool_name: str) -> bool:
        """True when ``approve`` recorded this exact name and it has not expired."""
        if not isinstance(tool_name, str):
            return False
        now = float(self._clock())
        with self._lock:
            entry = self._approved.get(tool_name)
            if entry is None:
                return False
            if _expired(entry, now):
                del self._approved[tool_name]
                return False
            return True

    def _purge(self, now: float) -> None:
        stale = [n for n, e in self._approved.items() if _expired(e, now)]
        for name in stale:
            del self._approved[name]


def _expired(entry: dict[str, Any], now: float) -> bool:
    expires_at = entry["expires_at"]
    return expires_at is not None and now >= expires_at


__all__ = ["ApprovalLog"]
