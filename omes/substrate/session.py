"""One Omes session as a substrate surface: brief-on-open plus the trail.

``SubstrateSession`` wraps a ``SubstrateClient`` with session identity and
provenance: ``open`` emits ``session.start``, fetches the brief, and caches
it (plus a ``.substrate/BRIEF.md`` fallback file); per-turn hooks emit the
prompt, tool calls, file edits, and a turn-end note; ``close`` emits
``session.end``. Every method is fail-open — the session never raises into
the loop — and tool arguments are never sent off-process.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any
from uuid import uuid4

BRIEF_FILENAME = "BRIEF.md"
BRIEF_DIRNAME = ".substrate"
PROMPT_SUMMARY_CHARS = 240
FILE_EDIT_TOOLS = ("write_file", "edit_file", "patch_file")


class SubstrateSession:
    """Session-scoped brief and event trail over one substrate client."""

    def __init__(
        self,
        client: Any,
        *,
        session_id: str | None = None,
        repo: str | None = None,
        branch: str | None = None,
        graph_id: str | None = None,
        brief_dir: str | Path | None = None,
        broker: Any = None,
    ) -> None:
        self._client = client
        self._session_id = session_id or uuid4().hex
        self._repo = repo
        self._branch = branch
        self._graph_id = graph_id
        self._brief_dir = Path(brief_dir) if brief_dir is not None else None
        self._broker = broker
        self._brief: str | None = None
        self._closed = False

    @property
    def session_id(self) -> str:
        """The id every event from this session carries."""
        return self._session_id

    def open(self) -> str:
        """Emit ``session.start`` and fetch the brief. Idempotent, never raises."""
        if self._brief is not None:
            return self._brief
        try:
            self._emit("session.start", f"omes session {self._session_id} opened")
            brief = self._client.brief(
                repo=self._repo, branch=self._branch, graph_id=self._graph_id
            )
            if not isinstance(brief, str):
                brief = ""
            self._brief = brief
            if brief and self._brief_dir is not None:
                target = self._brief_dir / BRIEF_DIRNAME / BRIEF_FILENAME
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(brief, encoding="utf-8")
        except Exception:
            self._brief = ""
        return self._brief

    def brief_block(self) -> str:
        """The cached brief as a prompt block, or ``""`` when none."""
        if not self._brief:
            return ""
        return f"## Substrate brief\n{self._brief}"

    def on_prompt(self, text: Any) -> None:
        """Emit the turn's prompt event. Never raises."""
        try:
            if isinstance(text, str):
                summary = text[:PROMPT_SUMMARY_CHARS]
            else:
                summary = f"<{type(text).__name__} prompt>"
            self._emit("prompt", self._redact(summary))
        except Exception:
            pass

    def on_tool_call(self, name: str, arguments: Any = None, ok: bool = True) -> None:
        """Emit ``tool.call`` (and ``file.edit`` for edit tools). Never raises."""
        try:
            tool = name if isinstance(name, str) and name else "<unknown tool>"
            self._emit("tool.call", f"{tool} {'ok' if ok else 'error'}")
            if tool in FILE_EDIT_TOOLS:
                path = _edit_path(arguments)
                if path is not None:
                    self._emit("file.edit", f"{tool} {path}")
        except Exception:
            pass

    def on_turn_end(self, exit_reason: Any) -> None:
        """Emit the turn-end note. Never raises."""
        with contextlib.suppress(Exception):
            self._emit("note", f"turn ended: {exit_reason}")

    def close(self) -> None:
        """Emit ``session.end``. Idempotent, never raises."""
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(Exception):
            self._emit("session.end", f"omes session {self._session_id} closed")

    def _emit(self, kind: str, summary: str) -> None:
        fields: dict[str, Any] = {"session_id": self._session_id}
        if self._repo is not None:
            fields["repo"] = self._repo
        if self._branch is not None:
            fields["branch"] = self._branch
        if self._graph_id is not None:
            fields["graph_id"] = self._graph_id
        self._client.emit(kind, summary, **fields)

    def _redact(self, text: str) -> str:
        if self._broker is None:
            return text
        try:
            return self._broker.redact(text)
        except Exception:
            return text


def _edit_path(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    path = arguments.get("path")
    return path if isinstance(path, str) and path else None


__all__ = ["BRIEF_DIRNAME", "BRIEF_FILENAME", "FILE_EDIT_TOOLS", "SubstrateSession"]
