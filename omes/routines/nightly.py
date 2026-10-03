"""Nightly learning: review transcripts through the curator, once each.

Each turn maps onto `review_turn`: the last non-steer user row becomes the
request text, tool rows become success/output pairs. Earned turns get
skills; every reviewed turn checkpoints so re-runs skip it. No model call —
the curator's earned-rule decides.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from omes.agent.curator import review_turn


def nightly_pass(
    directory: str | Path, skills_root: str | Path, turns: list[dict]
) -> dict:
    """Review each turn, checkpointing reviewed ids. Return creations."""
    if not isinstance(turns, list):
        raise ValueError("turns must be a list")
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("each turn must be a dict")
        if not isinstance(turn.get("id"), str) or turn["id"] == "":
            raise ValueError("each turn needs a non-blank string id")
        if not isinstance(turn.get("messages"), list):
            raise ValueError(f"turn {turn['id']!r} needs a messages list")
    try:
        Path(skills_root).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"cannot use skills root: {exc}") from exc
    state = _load(directory)
    reviewed = set(state["reviewed"])
    created: list[dict] = []
    fresh: list[str] = []
    for turn in turns:
        turn_id = turn["id"]
        if turn_id in reviewed:
            continue
        user_text, tool_results = _map(turn["messages"])
        outcome = review_turn(
            skills_root=skills_root, user_text=user_text, tool_results=tool_results
        )
        if outcome.get("created"):
            created.append({"turn_id": turn_id, "path": outcome.get("path")})
        reviewed.add(turn_id)
        fresh.append(turn_id)
        state["reviewed"] = sorted(reviewed)
        _write(directory, state)
    return {"created": created, "reviewed": fresh, "total_created": len(created)}


def _map(messages: list) -> tuple[str, list[dict]]:
    """Transcript rows to curator inputs. Steer rows are not requests."""
    user_text = ""
    for row in messages:
        if not isinstance(row, dict):
            continue
        if row.get("role") != "user" or row.get("display_kind") == "steer":
            continue
        content = row.get("content")
        if isinstance(content, str) and content:
            user_text = content
    tool_results: list[dict] = []
    for row in messages:
        if not isinstance(row, dict) or row.get("role") != "tool":
            continue
        output = row.get("content", "")
        if not isinstance(output, str):
            output = str(output)
        if output == "":
            continue
        tool_results.append(
            {"success": row.get("is_error") is not True, "output": output}
        )
    return user_text, tool_results


def _path(directory: str | Path) -> Path:
    return Path(directory) / "nightly.json"


def _load(directory: str | Path) -> dict[str, Any]:
    target = _path(directory)
    if not target.is_file():
        return {"reviewed": []}
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {target}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("reviewed"), list):
        raise ValueError(f"nightly state {target} has an unsupported shape")
    return document


def _write(directory: str | Path, state: dict) -> None:
    target = _path(directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(state, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".nightly.", suffix=".tmp")
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


__all__ = ["nightly_pass"]
