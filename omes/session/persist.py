"""JSON-document persistence for saved sessions and tasks.

Ports the ``packages/coding-agent/src/session/agent-storage.ts`` shape (one
versioned JSON document per id, written atomically) without the TUI session
machinery. A saved session holds a transcript plus metadata; a saved task
holds a title, a status, and notes. New handles on the same directory see
what earlier handles saved.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
TASK_STATUSES = ("open", "doing", "done")


def save_session(
    directory: str | Path,
    session_id: str,
    messages: list,
    metadata: dict | None = None,
) -> str:
    """Save a transcript. Return the file path."""
    _check_id(session_id)
    if not isinstance(messages, list) or any(
        not isinstance(row, dict) for row in messages
    ):
        raise ValueError("messages must be a list of dicts")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")
    return _write(
        directory,
        "sessions",
        session_id,
        {
            "schema": SCHEMA_VERSION,
            "id": session_id,
            "messages": messages,
            "metadata": metadata or {},
        },
    )


def load_session(directory: str | Path, session_id: str) -> dict:
    """Load a saved transcript. Unknown ids raise ``KeyError``."""
    _check_id(session_id)
    return _read(directory, "sessions", session_id)


def save_task(
    directory: str | Path,
    task_id: str,
    title: str,
    status: str = "open",
    notes: str = "",
) -> str:
    """Save a task. Return the file path."""
    _check_id(task_id)
    if not isinstance(title, str) or title == "":
        raise ValueError("title must be a non-empty string")
    if status not in TASK_STATUSES:
        raise ValueError(f"status must be one of {', '.join(TASK_STATUSES)}")
    if not isinstance(notes, str):
        raise ValueError("notes must be a string")
    return _write(
        directory,
        "tasks",
        task_id,
        {
            "schema": SCHEMA_VERSION,
            "id": task_id,
            "title": title,
            "status": status,
            "notes": notes,
        },
    )


def load_task(directory: str | Path, task_id: str) -> dict:
    """Load a saved task. Unknown ids raise ``KeyError``."""
    _check_id(task_id)
    return _read(directory, "tasks", task_id)


def _check_id(value: str) -> None:
    if not isinstance(value, str) or _ID.match(value) is None:
        raise ValueError(f"invalid id: {value!r}")


def _path(directory: str | Path, kind: str, item_id: str) -> Path:
    return Path(directory) / kind / f"{item_id}.json"


def _write(directory: str | Path, kind: str, item_id: str, document: dict) -> str:
    target = _path(directory, kind, item_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(document, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{item_id}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return str(target)


def _read(directory: str | Path, kind: str, item_id: str) -> dict[str, Any]:
    target = _path(directory, kind, item_id)
    if not target.is_file():
        raise KeyError(f"unknown {kind[:-1]}: {item_id}")
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {target}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema in {target}")
    return document


__all__ = [
    "SCHEMA_VERSION",
    "TASK_STATUSES",
    "load_session",
    "load_task",
    "save_session",
    "save_task",
]
