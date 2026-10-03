"""Checkpointed multi-step workflows.

Each step maps a JSON state dict to the next one; after every step the
checkpoint records how many steps are done plus the state. A step that
raises leaves the last checkpoint in place, and re-running skips finished
steps — resume runs only what never completed. Checkpoint files are written
atomically under `{directory}/workflows/{workflow_id}.json`.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def run_workflow(
    directory: str | Path,
    workflow_id: str,
    steps: list[Callable[[dict], dict]],
    state: dict | None = None,
) -> dict:
    """Run unfinished steps from the checkpoint. Return the final state."""
    _check_id(workflow_id)
    if not isinstance(steps, list) or not steps or any(
        not callable(step) for step in steps
    ):
        raise ValueError("steps must be a non-empty list of callables")
    checkpoint = load_checkpoint(directory, workflow_id)
    if checkpoint is not None:
        done = checkpoint.get("done", 0)
        current = checkpoint.get("state", {})
    else:
        done = 0
        current = dict(state) if state is not None else {}
    _check_state(current)
    for index in range(done, len(steps)):
        current = steps[index](dict(current))
        _check_state(current)
        _write(directory, workflow_id, {"done": index + 1, "state": current})
    return {"workflow_id": workflow_id, "state": current, "done": True}


def load_checkpoint(directory: str | Path, workflow_id: str) -> dict | None:
    """The checkpoint, or None when the workflow never ran."""
    _check_id(workflow_id)
    target = _path(directory, workflow_id)
    if not target.is_file():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {target}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"checkpoint {target} is not an object")
    return document


def _check_id(value: str) -> None:
    if not isinstance(value, str) or _ID.match(value) is None:
        raise ValueError(f"invalid id: {value!r}")


def _check_state(state: Any) -> None:
    if not isinstance(state, dict):
        raise ValueError("workflow state must be a JSON-serializable dict")
    try:
        json.dumps(state)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"workflow state is not JSON-serializable: {exc}") from exc


def _path(directory: str | Path, workflow_id: str) -> Path:
    return Path(directory) / "workflows" / f"{workflow_id}.json"


def _write(directory: str | Path, workflow_id: str, document: dict) -> None:
    target = _path(directory, workflow_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(document, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{workflow_id}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


__all__ = ["load_checkpoint", "run_workflow"]
