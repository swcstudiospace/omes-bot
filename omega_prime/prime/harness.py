"""Typed connector over the continual-harness port (CONN-01).

Sits between the ``harness_*`` tool handlers and
``omega_prime/learning/harness.py`` (``HarnessState``). Kinds and scopes are
the closed Prime vocabularies; entry shape validation lives in the
capability module and is surfaced here as typed requests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, cast

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


class HarnessConnector:
    """The typed boundary over ``HarnessState`` (one connector per root)."""

    def __init__(self, root: Any) -> None:
        self._root = root

    def _state(self, scope: str) -> HarnessState:
        if scope not in SCOPES:
            raise PrimeError("bad_value", f"scope must be one of {', '.join(SCOPES)}")
        return HarnessState(self._root, scope=scope).load()

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

    def get(self, kind: str, id: str, *, scope: str = "local") -> dict:
        state = self._state(scope)
        entry = state.get(self._kind(kind), id)
        return {
            "entry": None if entry is None else EntryView.from_entry(entry).to_dict()
        }

    def list_entries(self, kind: str | None = None, *, scope: str = "local") -> dict:
        state = self._state(scope)
        checked = None if kind is None else self._kind(kind)
        return {
            "entries": [
                EntryView.from_entry(e).to_dict() for e in state.list_entries(checked)
            ]
        }

    def delete(self, kind: str, id: str, *, scope: str = "local") -> dict:
        state = self._state(scope)
        deleted = state.delete(self._kind(kind), id)
        if deleted:
            state.save()
        return {"deleted": deleted}

    def rollback(self, *, scope: str = "local") -> dict:
        state = self._state(scope)
        restored = state.rollback()
        if restored:
            state.save()
        return {"restored": restored}


__all__ = ["SCHEMA_VERSION", "EntryView", "HarnessConnector", "UpsertRequest"]
