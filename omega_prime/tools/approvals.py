"""In-process approval log for gated tools.

Adapted from Hermes ``tools/approval.py`` ``approve_session``. This log only
records a name. It has no gateway queue and no prompt. The bot cannot approve
its own tool.
"""

from __future__ import annotations

from typing import Any


class ApprovalLog:
    """Names a person has approved. A refused ``approve`` records nothing."""

    def __init__(self) -> None:
        self._approved: set[str] = set()

    def approve(
        self,
        tool_name: str,
        approved_by: str,
        *,
        bot_id: str = "bot-00-omega-prime",
    ) -> dict[str, Any]:
        """Record ``tool_name`` when ``approved_by`` is a person, not ``bot_id``."""
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
        self._approved.add(tool_name)
        return {
            "approved": True,
            "tool": tool_name,
            "approved_by": approved_by,
            "bot_id": bot_id,
        }

    def is_approved(self, tool_name: str) -> bool:
        """True when ``approve`` recorded this exact name."""
        return isinstance(tool_name, str) and tool_name in self._approved


__all__ = ["ApprovalLog"]
