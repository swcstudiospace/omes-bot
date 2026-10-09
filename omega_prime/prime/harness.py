# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over the continual-harness port (CONN-01).

Sits between the ``harness_*`` tool handlers and
``omega_prime/learning/harness.py`` (``HarnessState``). Kinds and scopes are
the closed Prime vocabularies; entry shape validation lives in the
capability module and is surfaced here as typed requests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

from omega_prime.agent.refine import refine
from omega_prime.learning.harness import (
    KINDS,
    SCOPES,
    HarnessEntry,
    HarnessKind,
    HarnessState,
)
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    reject_unknown,
    require_member,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_UPSERT_FIELDS = frozenset(
    {"schema_version", "kind", "scope", "id", "title", "body", "tags"}
)
_GET_FIELDS = frozenset({"schema_version", "kind", "scope", "id"})
_LIST_FIELDS = frozenset({"schema_version", "kind", "scope"})
_DELETE_FIELDS = frozenset({"schema_version", "kind", "scope", "id"})
_REFINE_FIELDS = frozenset(
    {"schema_version", "trigger", "proposals", "trajectory", "scope"}
)
_ROLLBACK_FIELDS = frozenset({"schema_version", "scope"})


def _scope_of(payload: dict, *, what: str) -> str:
    if "scope" not in payload:
        return "local"
    return require_member(payload, "scope", SCOPES, what=what)


@dataclass(frozen=True)
class UpsertRequest:
    kind: str
    id: str
    title: str
    body: str
    scope: str = "local"
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Any) -> UpsertRequest:
        payload = require_payload(raw, what="UpsertRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="UpsertRequest")
        reject_unknown(payload, _UPSERT_FIELDS, what="UpsertRequest")
        tags = payload.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise PrimeError("bad_type", "UpsertRequest.tags must be a list of strings")
        return cls(
            kind=require_member(payload, "kind", KINDS, what="UpsertRequest"),
            id=require_str(payload, "id", what="UpsertRequest"),
            title=require_str(payload, "title", what="UpsertRequest"),
            body=require_str(payload, "body", what="UpsertRequest"),
            scope=require_member(payload, "scope", SCOPES, what="UpsertRequest")
            if "scope" in payload
            else "local",
            tags=tuple(tags),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": self.kind,
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "scope": self.scope,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class EntryView:
    """The JSON-safe view of one ``HarnessEntry``."""

    kind: str
    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_entry(cls, entry: HarnessEntry) -> EntryView:
        if entry.kind not in KINDS:
            raise PrimeError("bad_value", f"entry kind {entry.kind!r} not in KINDS")
        return cls(
            kind=entry.kind,
            id=entry.id,
            title=entry.title,
            body=entry.body,
            tags=list(entry.tags),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    @classmethod
    def from_dict(cls, raw: Any) -> EntryView:
        payload = require_payload(raw, what="EntryView")
        kind = payload.get("kind")
        if kind not in KINDS:
            raise PrimeError("bad_value", f"EntryView.kind {kind!r} not in KINDS")
        tags = payload.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise PrimeError("bad_type", "EntryView.tags must be a list of strings")
        body = payload.get("body")
        return cls(
            kind=kind,
            id=require_str(payload, "id", what="EntryView"),
            title=require_str(payload, "title", what="EntryView"),
            body=body if isinstance(body, str) else "",
            tags=tags,
            created_at=payload.get("created_at") or "",
            updated_at=payload.get("updated_at") or "",
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GetRequest:
    kind: str
    id: str
    scope: str = "local"

    @classmethod
    def from_dict(cls, raw: Any) -> GetRequest:
        payload = require_payload(raw, what="GetRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="GetRequest")
        reject_unknown(payload, _GET_FIELDS, what="GetRequest")
        return cls(
            kind=require_member(payload, "kind", KINDS, what="GetRequest"),
            id=require_str(payload, "id", what="GetRequest"),
            scope=_scope_of(payload, what="GetRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ListRequest:
    kind: str | None = None
    scope: str = "local"

    @classmethod
    def from_dict(cls, raw: Any) -> ListRequest:
        payload = require_payload(raw, what="ListRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ListRequest")
        reject_unknown(payload, _LIST_FIELDS, what="ListRequest")
        kind = payload.get("kind")
        if kind is not None:
            kind = require_member(payload, "kind", KINDS, what="ListRequest")
        return cls(kind=kind, scope=_scope_of(payload, what="ListRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class DeleteRequest:
    kind: str
    id: str
    scope: str = "local"

    @classmethod
    def from_dict(cls, raw: Any) -> DeleteRequest:
        payload = require_payload(raw, what="DeleteRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="DeleteRequest")
        reject_unknown(payload, _DELETE_FIELDS, what="DeleteRequest")
        return cls(
            kind=require_member(payload, "kind", KINDS, what="DeleteRequest"),
            id=require_str(payload, "id", what="DeleteRequest"),
            scope=_scope_of(payload, what="DeleteRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class RefineRequest:
    trigger: str
    proposals: list
    trajectory: Any
    scope: str = "local"

    @classmethod
    def from_dict(cls, raw: Any) -> RefineRequest:
        payload = require_payload(raw, what="RefineRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="RefineRequest")
        reject_unknown(payload, _REFINE_FIELDS, what="RefineRequest")
        proposals = payload.get("proposals")
        if not isinstance(proposals, list) or any(
            not isinstance(p, dict) for p in proposals
        ):
            raise PrimeError(
                "bad_type", "RefineRequest.proposals must be a list of objects"
            )
        if "trajectory" not in payload:
            raise PrimeError("bad_type", "RefineRequest.trajectory is required")
        return cls(
            trigger=require_str(payload, "trigger", what="RefineRequest"),
            proposals=proposals,
            trajectory=payload["trajectory"],
            scope=_scope_of(payload, what="RefineRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class RollbackRequest:
    scope: str = "local"

    @classmethod
    def from_dict(cls, raw: Any) -> RollbackRequest:
        payload = require_payload(raw, what="RollbackRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="RollbackRequest")
        reject_unknown(payload, _ROLLBACK_FIELDS, what="RollbackRequest")
        return cls(scope=_scope_of(payload, what="RollbackRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


class HarnessConnector:
    """The typed boundary over ``HarnessState`` (one connector per root).

    Local and global scopes live in sibling subdirectories of the root, the
    same layout the registered ``harness_*`` tools have always used, so a
    global write never collides with the session-local store.
    """

    def __init__(self, root: Any) -> None:
        self._root = root

    def _state(self, scope: str) -> HarnessState:
        if scope not in SCOPES:
            raise PrimeError("bad_value", f"scope must be one of {', '.join(SCOPES)}")
        base = Path(self._root) / (
            "harness-global" if scope == "global" else "harness-local"
        )
        return HarnessState(base, scope=scope).load()  # type: ignore[arg-type]

    @staticmethod
    def _kind(value: str) -> HarnessKind:
        if value not in KINDS:
            raise PrimeError(
                "bad_value", f"kind must be one of {', '.join(KINDS)}; got {value!r}"
            )
        return cast("HarnessKind", value)

    def upsert(self, request: UpsertRequest) -> dict:
        state = self._state(request.scope)
        entry = state.upsert(
            self._kind(request.kind),
            request.id,
            title=request.title,
            body=request.body,
            tags=list(request.tags),
        )
        state.save()
        return {"entry": EntryView.from_entry(entry).to_dict()}

    def get(self, request: GetRequest) -> dict:
        state = self._state(request.scope)
        entry = state.get(self._kind(request.kind), request.id)
        return {
            "entry": None if entry is None else EntryView.from_entry(entry).to_dict()
        }

    def list_entries(self, request: ListRequest) -> dict:
        state = self._state(request.scope)
        checked = None if request.kind is None else self._kind(request.kind)
        return {
            "entries": [
                EntryView.from_entry(e).to_dict() for e in state.list_entries(checked)
            ]
        }

    def delete(self, request: DeleteRequest) -> dict:
        state = self._state(request.scope)
        deleted = state.delete(self._kind(request.kind), request.id)
        if deleted:
            state.save()
        return {"deleted": deleted}

    def refine(self, request: RefineRequest) -> dict:
        state = self._state(request.scope)
        result = refine(
            state,
            trigger=request.trigger,
            proposals=list(request.proposals),
            trajectory=request.trajectory,
        )
        if result["applied"]:
            state.save()
        return result

    def rollback(self, request: RollbackRequest) -> dict:
        state = self._state(request.scope)
        restored = state.rollback()
        if restored:
            state.save()
        return {"restored": restored}


__all__ = [
    "SCHEMA_VERSION",
    "DeleteRequest",
    "EntryView",
    "GetRequest",
    "HarnessConnector",
    "ListRequest",
    "RefineRequest",
    "RollbackRequest",
    "UpsertRequest",
]
