"""Agent-side command screen. A check runs before the action.

Ports the ``packages/coding-agent/src/security`` preflight shape as a pure
argv verdict: privilege-escalation binaries, filesystem-wide deletes, and
malformed argv are refused with a reason. ``raw`` shell strings never reach
here — callers spawn argv with ``shell=False`` — so operators like ``|`` are
literal arguments, not a bypass.
"""

from __future__ import annotations

import os
from typing import Any

_ESCALATE = frozenset(
    {
        "sudo",
        "su",
        "doas",
        "runas",
        "mkfs",
        "dd",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
    }
)


def screen_argv(argv: Any) -> dict:
    """Return ``{"ok": True}`` or ``{"ok": False, "reason": ...}``."""
    if not isinstance(argv, list) or not argv:
        return {"ok": False, "reason": "argv must be a non-empty list"}
    for part in argv:
        if not isinstance(part, str) or part == "":
            return {"ok": False, "reason": "argv parts must be non-empty strings"}
        if "\x00" in part:
            return {"ok": False, "reason": "argv must not contain NUL"}
    program = os.path.basename(argv[0])
    if program in _ESCALATE:
        return {"ok": False, "reason": f"refused binary: {program}"}
    if program == "rm":
        if "--no-preserve-root" in argv[1:]:
            return {"ok": False, "reason": "refused rm --no-preserve-root"}
        if "/" in argv[1:]:
            return {"ok": False, "reason": "refused rm on /"}
    return {"ok": True}


__all__ = ["screen_argv"]
