"""One objective with steps, persisted as a versioned JSON document.

Ports the ``packages/coding-agent/src/goals`` state shape (objective plus
ordered steps with completion) without the mode runtime. Every mutation
rewrites the file atomically, so a new store on the same directory sees the
old state.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class GoalStore:
    """``{"objective", "steps": [{"text", "done"}]}`` on disk."""

    def __init__(self, directory: str | Path) -> None:
        self.path = Path(directory) / "goals.json"
        self._document = self._load()

    def set_objective(self, text: str) -> dict:
        """Replace the objective. Blank text is a ``ValueError``."""
        if not isinstance(text, str) or text.strip() == "":
            raise ValueError("objective must be a non-empty string")
        self._document["objective"] = text
        self._save()
        return self.status()

    def add_step(self, text: str) -> dict:
        """Append an unfinished step."""
        if not isinstance(text, str) or text.strip() == "":
            raise ValueError("step must be a non-empty string")
        self._document["steps"].append({"text": text, "done": False})
        self._save()
        return self.status()

    def complete_step(self, index: int) -> dict:
        """Mark step ``index`` done. Out of range is an ``IndexError``."""
        steps = self._document["steps"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < len(steps)
        ):
            raise IndexError(f"no such step: {index!r}")
        steps[index]["done"] = True
        self._save()
        return self.status()

    def status(self) -> dict[str, Any]:
        """A copy of the objective and steps."""
        return {
            "objective": self._document["objective"],
            "steps": [dict(step) for step in self._document["steps"]],
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"schema": SCHEMA_VERSION, "objective": "", "steps": []}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load {self.path}: {exc}") from exc
        if not isinstance(document, dict) or document.get("schema") != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema in {self.path}")
        if not isinstance(document.get("objective"), str) or not isinstance(
            document.get("steps"), list
        ):
            raise ValueError(f"unsupported schema in {self.path}")
        return document

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(self._document, indent=2, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".goals.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


__all__ = ["SCHEMA_VERSION", "GoalStore"]
