"""Engagement sweep: fresh mentions in, queued reply drafts out.

Each mention checkpoints as it is drafted, so an interrupted sweep resumes
without duplicating drafts. The composer is injected — tests use a stub,
production wires a model turn. The sweep never publishes: drafts queue for
a human or an approved job.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def sweep_mentions(
    client: Any,
    composer: Callable[[dict], str],
    *,
    directory: str | Path,
    sweep_id: str,
    user_id: str | None = None,
    max_results: int = 10,
) -> dict:
    """Draft one reply per fresh mention. Return this run's drafts."""
    if not isinstance(sweep_id, str) or _ID.match(sweep_id) is None:
        raise ValueError(f"invalid sweep id: {sweep_id!r}")
    if not callable(composer):
        raise ValueError("composer must be callable")
    state = _load(directory, sweep_id)
    drafted = set(state["drafted"])
    skipped = set(state["skipped"])
    fresh_drafts: list[dict] = []
    fresh_skipped: list[str] = []
    mentions = client.mentions(user_id=user_id, max_results=max_results)
    for mention in mentions.get("posts", []):
        if not isinstance(mention, dict):
            continue
        mention_id = mention.get("id")
        if not isinstance(mention_id, str) or mention_id == "":
            continue
        if mention_id in drafted or mention_id in skipped:
            continue
        text = composer(mention)
        if not isinstance(text, str) or text.strip() == "":
            skipped.add(mention_id)
            fresh_skipped.append(mention_id)
        else:
            draft = {"mention_id": mention_id, "reply_to": mention_id, "text": text}
            state["drafts"].append(draft)
            drafted.add(mention_id)
            fresh_drafts.append(draft)
        state["drafted"] = sorted(drafted)
        state["skipped"] = sorted(skipped)
        _write(directory, sweep_id, state)
    return {
        "sweep_id": sweep_id,
        "drafts": fresh_drafts,
        "skipped": fresh_skipped,
        "total": len(state["drafts"]),
    }


def load_sweep(directory: str | Path, sweep_id: str) -> dict | None:
    """The sweep state, or None when the sweep never ran."""
    if not isinstance(sweep_id, str) or _ID.match(sweep_id) is None:
        raise ValueError(f"invalid sweep id: {sweep_id!r}")
    target = _path(directory, sweep_id)
    if not target.is_file():
        return None
    return _load(directory, sweep_id)


def _load(directory: str | Path, sweep_id: str) -> dict[str, Any]:
    target = _path(directory, sweep_id)
    if not target.is_file():
        return {"drafted": [], "drafts": [], "skipped": []}
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {target}: {exc}") from exc
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("drafted"), list)
        or not isinstance(document.get("drafts"), list)
        or not isinstance(document.get("skipped"), list)
    ):
        raise ValueError(f"sweep state {target} has an unsupported shape")
    return document


def _path(directory: str | Path, sweep_id: str) -> Path:
    return Path(directory) / "sweeps" / f"{sweep_id}.json"


def _write(directory: str | Path, sweep_id: str, state: dict) -> None:
    target = _path(directory, sweep_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(state, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{sweep_id}.", suffix=".tmp"
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


__all__ = ["load_sweep", "sweep_mentions"]
