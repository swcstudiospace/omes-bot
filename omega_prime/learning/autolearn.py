"""Capture lessons as skills after a substantive turn.

Ports the ``packages/coding-agent/src/autolearn`` controller's capture half:
after a turn with enough tool calls, the lesson is written as a skill. The
only writer is the phase 4 skill manager (``skill_manage``); this module
never touches the skills tree itself. The standing-guidance half
(``buildAutoLearnInstructions``) is a prompt concern and stays out.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega_prime.skills_runtime.manager import skill_manage


class Autolearn:
    """Record lessons. ``min_tool_calls`` gates insubstantial turns."""

    def __init__(self, skills_root: str | Path, *, min_tool_calls: int = 1) -> None:
        self.skills_root = skills_root
        self.min_tool_calls = min_tool_calls

    def consider_turn(self, tool_calls: int, name: str, content: str) -> dict:
        """Write the lesson unless the turn was insubstantial or blank."""
        if not isinstance(tool_calls, int) or tool_calls < self.min_tool_calls:
            return {
                "learned": False,
                "reason": f"fewer than {self.min_tool_calls} tool calls",
            }
        if not isinstance(name, str) or name.strip() == "":
            return {"learned": False, "reason": "skill name is blank"}
        if not isinstance(content, str) or content.strip() == "":
            return {"learned": False, "reason": "skill content is blank"}
        try:
            Path(self.skills_root).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"learned": False, "reason": f"cannot use skills root: {exc}"}
        created = _parse(
            skill_manage("create", name, content, skills_root=self.skills_root)
        )
        if "error" not in created:
            return {"learned": True, "skill": name}
        if "already exists" not in str(created.get("error", "")):
            return {"learned": False, "reason": str(created.get("error"))}
        edited = _parse(
            skill_manage("edit", name, content, skills_root=self.skills_root)
        )
        if "error" in edited:
            return {"learned": False, "reason": str(edited.get("error"))}
        return {"learned": True, "skill": name}


def _parse(payload: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {"error": "skill manager returned invalid JSON"}
    return parsed if isinstance(parsed, dict) else {"error": "skill manager failed"}


__all__ = ["Autolearn"]
