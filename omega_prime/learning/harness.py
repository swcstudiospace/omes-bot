# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Continual harness state store — a behavior port of Prime Agent's harness.

Source: ``prime-agent/prime-agent-runtime/src/rlm/harness.py`` @ ``967eb13f``
(MIT, PrimeIntellect — see VENDOR.md).

The state model mirrors Prime's exactly: five kinds (prompt, memory, skill,
subagent, factory), session-local scope by default with an opt-in global
scope, strict per-kind entry-shape validation, and refinement events that
require trigger + changes + evidence + outcome — evidence is mandatory, the
"evidence-backed updates only" rule. Every applied refinement snapshots the
prior state so rollback restores the exact prior bytes.

Single-process Omega Prime needs no lock-dir; save refuses to clobber a file
whose mtime changed since load (the port of ``_sync_from_disk``'s intent).
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

HarnessKind = Literal["prompt", "memory", "skill", "subagent", "factory"]
HarnessScope = Literal["local", "global"]

KINDS: tuple[HarnessKind, ...] = ("prompt", "memory", "skill", "subagent", "factory")
SCOPES: tuple[HarnessScope, ...] = ("local", "global")

_DEFAULT_FILE_NAME = "harness_state.json"
_HARNESS_DIR_NAME = "harness"


@dataclass(frozen=True)
class HarnessEntry:
    """One supplemental harness entry (verbatim Prime field names)."""

    kind: str
    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class RefinementEvent:
    """One recorded refinement. ``evidence`` is mandatory (Prime contract)."""

    trigger: str
    changes: dict[str, Any]
    evidence: list[str]
    outcome: str
    at: str = ""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _validate_entry_shape(kind: str, entry: dict[str, Any]) -> None:
    """Reject malformed entries (the Prime ``_validate_entry_shape`` port)."""
    if kind not in KINDS:
        raise ValueError(f"unknown harness kind: {kind!r}")
    if not isinstance(entry.get("id"), str) or not entry["id"]:
        raise ValueError(f"harness {kind} entry requires a non-empty id")
    if not isinstance(entry.get("title"), str) or not entry["title"]:
        raise ValueError(f"harness {kind} entry {entry['id']!r} requires a title")
    if not isinstance(entry.get("body"), str):
        raise ValueError(f"harness {kind} entry {entry['id']!r} requires a body string")
    tags = entry.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ValueError(f"harness {kind} entry {entry['id']!r} tags must be strings")


def _validate_refinement_event(event: dict[str, Any]) -> None:
    """Evidence-backed updates only (Prime ``_validate_refinement_event``)."""
    if not isinstance(event.get("trigger"), str) or not event["trigger"]:
        raise ValueError("refinement event requires a trigger")
    if not isinstance(event.get("changes"), dict):
        raise ValueError("refinement event requires a changes object")
    evidence = event.get("evidence")
    if (
        not isinstance(evidence, list)
        or not evidence
        or not all(isinstance(e, str) and e for e in evidence)
    ):
        raise ValueError("refinement event requires non-empty evidence")
    if not isinstance(event.get("outcome"), str) or not event["outcome"]:
        raise ValueError("refinement event requires an outcome")


class HarnessState:
    """One scope's harness store, backed by ``harness_state.json``."""

    def __init__(self, root: str | Path, *, scope: HarnessScope = "local") -> None:
        if scope not in SCOPES:
            raise ValueError(f"unknown harness scope: {scope!r}")
        self._root = Path(root)
        self._scope: HarnessScope = scope
        self._entries: dict[str, dict[str, HarnessEntry]] = {k: {} for k in KINDS}
        self._events: list[RefinementEvent] = []
        self._snapshots: list[dict[str, Any]] = []
        self._loaded_mtime: float | None = None

    @property
    def scope(self) -> str:
        return self._scope

    @property
    def path(self) -> Path:
        return self._root / _HARNESS_DIR_NAME / _DEFAULT_FILE_NAME

    # -- persistence --------------------------------------------------------

    def load(self) -> HarnessState:
        if not self.path.is_file():
            return self
        document = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"{self.path} must contain a JSON object")
        for kind, entries in document.get("entries", {}).items():
            for entry in entries.values():
                _validate_entry_shape(kind, entry)
                self._entries[kind][entry["id"]] = HarnessEntry(
                    kind=kind,
                    id=entry["id"],
                    title=entry["title"],
                    body=entry["body"],
                    tags=list(entry.get("tags", [])),
                    created_at=entry.get("created_at", ""),
                    updated_at=entry.get("updated_at", ""),
                )
        for event in document.get("refinements", []):
            _validate_refinement_event(event)
            self._events.append(
                RefinementEvent(
                    trigger=event["trigger"],
                    changes=dict(event["changes"]),
                    evidence=list(event["evidence"]),
                    outcome=event["outcome"],
                    at=event.get("at", ""),
                )
            )
        self._snapshots = list(document.get("snapshots", []))
        self._loaded_mtime = self.path.stat().st_mtime
        return self

    def save(self) -> HarnessState:
        if (
            self._loaded_mtime is not None
            and self.path.is_file()
            and self.path.stat().st_mtime != self._loaded_mtime
        ):
            raise RuntimeError(
                f"{self.path} changed on disk since load; refusing to clobber"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "version": 1,
            "scope": self._scope,
            "entries": {
                kind: {eid: asdict(entry) for eid, entry in entries.items()}
                for kind, entries in self._entries.items()
            },
            "refinements": [asdict(event) for event in self._events],
            "snapshots": self._snapshots,
        }
        self.path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._loaded_mtime = self.path.stat().st_mtime
        return self

    # -- CRUD -----------------------------------------------------------------

    def upsert(
        self,
        kind: HarnessKind,
        id: str,
        *,
        title: str,
        body: str,
        tags: list[str] | None = None,
    ) -> HarnessEntry:
        existing = self._entries.get(kind, {}).get(id)
        entry = HarnessEntry(
            kind=kind,
            id=id,
            title=title,
            body=body,
            tags=list(tags or []),
            created_at=existing.created_at if existing else _now(),
            updated_at=_now(),
        )
        _validate_entry_shape(kind, asdict(entry))
        self._entries[kind][id] = entry
        return entry

    def get(self, kind: HarnessKind, id: str) -> HarnessEntry | None:
        return self._entries.get(kind, {}).get(id)

    def list_entries(self, kind: HarnessKind | None = None) -> list[HarnessEntry]:
        if kind is not None:
            return list(self._entries.get(kind, {}).values())
        return [
            entry for entries in self._entries.values() for entry in entries.values()
        ]

    def delete(self, kind: HarnessKind, id: str) -> bool:
        return self._entries.get(kind, {}).pop(id, None) is not None

    # -- refinement + rollback -------------------------------------------------

    def record_refinement(
        self,
        *,
        trigger: str,
        changes: dict[str, Any],
        evidence: list[str],
        outcome: str,
    ) -> RefinementEvent:
        """Snapshot the current state, then record the evidence-backed event."""
        event = RefinementEvent(
            trigger=trigger,
            changes=dict(changes),
            evidence=list(evidence),
            outcome=outcome,
            at=_now(),
        )
        _validate_refinement_event(asdict(event))
        self._snapshots.append(
            {
                "at": _now(),
                "entries": copy.deepcopy(
                    {
                        k: {eid: asdict(e) for eid, e in entries.items()}
                        for k, entries in self._entries.items()
                    }
                ),
            }
        )
        self._events.append(event)
        return event

    def rollback(self) -> bool:
        """Restore the most recent snapshot exactly. False when none exists."""
        if not self._snapshots:
            return False
        snapshot = self._snapshots.pop()
        self._entries = {
            kind: {eid: HarnessEntry(**entry) for eid, entry in entries.items()}
            for kind, entries in snapshot["entries"].items()
        }
        return True

    @property
    def refinement_events(self) -> list[RefinementEvent]:
        return list(self._events)

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)


__all__ = [
    "KINDS",
    "SCOPES",
    "HarnessEntry",
    "HarnessState",
    "RefinementEvent",
]
