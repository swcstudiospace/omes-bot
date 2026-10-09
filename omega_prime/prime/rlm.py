# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over the RLM recursion port (CONN-01).

Sits between the ``rlm_*`` tool handlers (JSON dicts) and
``omega_prime/agent/rlm.py`` (``RlmHost`` / ``NoRlmHost``). Requests and
responses are frozen dataclasses with strict ``from_dict`` decoders; the
closed status vocabularies are the verbatim Prime sets from the capability
module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from omega_prime.agent.rlm import (
    ACTIVITY_KINDS,
    COLLECT_STATUSES,
    SUBAGENT_STATUSES,
    RLMChildResult,
    RLMSubagent,
)
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    optional_str,
    reject_unknown,
    require_int,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_SPAWN_FIELDS = frozenset({"schema_version", "prompt", "name", "model", "thinking"})
_COLLECT_FIELDS = frozenset({"schema_version", "targets", "timeout_ms"})
_PROGRESS_FIELDS = frozenset({"schema_version", "child_id", "message"})
_CREATE_SESSION_FIELDS = frozenset(
    {"schema_version", "prompt", "name", "model", "thinking", "cwd"}
)
_DELETE_FIELDS = frozenset({"schema_version", "target"})
_RENAME_FIELDS = frozenset({"schema_version", "target", "name"})
_LIST_SUBAGENTS_FIELDS = frozenset({"schema_version"})


def _check_selector(value: Any, *, what: str) -> Any:
    """Validate one child selector without narrowing the host's shapes.

    The host accepts a spawn handle, a subagent row, or a name/id string;
    over the JSON boundary those arrive as a dict row or a string. A
    malformed selector is a typed error, never an implicit empty selection.
    """
    if isinstance(value, bool):
        raise PrimeError("bad_type", f"{what} must be a string or handle row")
    if isinstance(value, str):
        if not value.strip():
            raise PrimeError("bad_value", f"{what} must be a non-empty string")
        return value
    if isinstance(value, dict):
        child_id = value.get("rlm_child_id")
        if not isinstance(child_id, str) or not child_id.strip():
            raise PrimeError(
                "bad_type", f"{what} handle rows must carry a rlm_child_id string"
            )
        return value
    raise PrimeError("bad_type", f"{what} must be a string or handle row")


def _nonblank_name(name: str, *, what: str) -> str:
    """Reject a present-but-blank child name."""
    if not name.strip():
        raise PrimeError("bad_value", f"{what}.name must not be blank")
    return name


def _optional_name(payload: dict, *, what: str) -> str | None:
    """An optional child name: ``None``/absent stays allowed, blank does not."""
    name = optional_str(payload, "name", what=what)
    return None if name is None else _nonblank_name(name, what=what)


@dataclass(frozen=True)
class SpawnRequest:
    prompt: str
    name: str
    model: str | None = None
    thinking: str | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> SpawnRequest:
        payload = require_payload(raw, what="SpawnRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="SpawnRequest")
        reject_unknown(payload, _SPAWN_FIELDS, what="SpawnRequest")
        return cls(
            prompt=require_str(payload, "prompt", what="SpawnRequest"),
            name=_nonblank_name(
                require_str(payload, "name", what="SpawnRequest"), what="SpawnRequest"
            ),
            model=optional_str(payload, "model", what="SpawnRequest"),
            thinking=optional_str(payload, "thinking", what="SpawnRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class CollectRequest:
    targets: Any = None
    timeout_ms: int = 0

    @classmethod
    def from_dict(cls, raw: Any) -> CollectRequest:
        payload = require_payload(raw, what="CollectRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="CollectRequest")
        reject_unknown(payload, _COLLECT_FIELDS, what="CollectRequest")
        targets = payload.get("targets")
        if targets is None or targets == []:
            checked = targets
        elif isinstance(targets, list):
            checked = []
            for entry in targets:
                if isinstance(entry, bool) or not isinstance(entry, (str, dict)):
                    raise PrimeError(
                        "bad_type",
                        "CollectRequest.targets entries must be strings or handle rows",
                    )
                checked.append(_check_selector(entry, what="CollectRequest.targets"))
        elif isinstance(targets, (str, dict)):
            checked = _check_selector(targets, what="CollectRequest.targets")
        else:
            raise PrimeError(
                "bad_type",
                "CollectRequest.targets must be a string, list, dict, or null",
            )
        return cls(
            targets=checked,
            timeout_ms=require_int(payload, "timeout_ms", what="CollectRequest")
            if "timeout_ms" in payload
            else 0,
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ProgressNoteRequest:
    child_id: str
    message: str

    @classmethod
    def from_dict(cls, raw: Any) -> ProgressNoteRequest:
        payload = require_payload(raw, what="ProgressNoteRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ProgressNoteRequest")
        reject_unknown(payload, _PROGRESS_FIELDS, what="ProgressNoteRequest")
        return cls(
            child_id=require_str(payload, "child_id", what="ProgressNoteRequest"),
            message=require_str(payload, "message", what="ProgressNoteRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class CreateSessionRequest:
    prompt: str
    name: str | None = None
    model: str | None = None
    thinking: str | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> CreateSessionRequest:
        payload = require_payload(raw, what="CreateSessionRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="CreateSessionRequest")
        reject_unknown(payload, _CREATE_SESSION_FIELDS, what="CreateSessionRequest")
        # The pinned kernel SDK sends ``cwd=None``; any directory is refused
        # because children share the host process directory.
        if payload.get("cwd") is not None:
            raise PrimeError(
                "bad_value",
                "CreateSessionRequest.cwd is not supported: per-session working "
                "directories do not exist, children share the host process directory",
            )
        return cls(
            prompt=require_str(payload, "prompt", what="CreateSessionRequest"),
            name=_optional_name(payload, what="CreateSessionRequest"),
            model=optional_str(payload, "model", what="CreateSessionRequest"),
            thinking=optional_str(payload, "thinking", what="CreateSessionRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class DeleteRequest:
    target: Any

    @classmethod
    def from_dict(cls, raw: Any) -> DeleteRequest:
        payload = require_payload(raw, what="DeleteRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="DeleteRequest")
        reject_unknown(payload, _DELETE_FIELDS, what="DeleteRequest")
        if "target" not in payload:
            raise PrimeError("bad_type", "DeleteRequest.target is required")
        return cls(
            target=_check_selector(payload["target"], what="DeleteRequest.target")
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class RenameRequest:
    target: Any
    name: str

    @classmethod
    def from_dict(cls, raw: Any) -> RenameRequest:
        payload = require_payload(raw, what="RenameRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="RenameRequest")
        reject_unknown(payload, _RENAME_FIELDS, what="RenameRequest")
        target = payload.get("target")
        if target is not None:
            target = _check_selector(target, what="RenameRequest.target")
        return cls(
            target=target,
            name=_nonblank_name(
                require_str(payload, "name", what="RenameRequest"),
                what="RenameRequest",
            ),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ChildResultView:
    """The JSON-safe view of one ``RLMChildResult`` (Path → str)."""

    rlm_child_id: str
    session_name: str | None
    session_dir: str | None
    status: str
    settled: bool
    answer_preview: str | None
    error: str | None
    duration_ms: int | None
    tool_use_count: int | None
    replied_since_task: bool | None

    @classmethod
    def from_result(cls, result: RLMChildResult) -> ChildResultView:
        if result.status not in COLLECT_STATUSES:
            raise PrimeError(
                "bad_value",
                f"child result status {result.status!r} not in COLLECT_STATUSES",
            )
        return cls(
            rlm_child_id=result.rlm_child_id,
            session_name=result.session_name,
            session_dir=str(result.session_dir)
            if result.session_dir is not None
            else None,
            status=result.status,
            settled=result.settled,
            answer_preview=result.answer_preview,
            error=result.error,
            duration_ms=result.duration_ms,
            tool_use_count=result.tool_use_count,
            replied_since_task=result.replied_since_task,
        )

    @classmethod
    def from_dict(cls, raw: Any) -> ChildResultView:
        payload = require_payload(raw, what="ChildResultView")
        status = payload.get("status")
        if status not in COLLECT_STATUSES:
            raise PrimeError(
                "bad_value",
                f"ChildResultView.status {status!r} not in COLLECT_STATUSES",
            )
        settled = payload.get("settled")
        if not isinstance(settled, bool):
            raise PrimeError("bad_type", "ChildResultView.settled must be bool")
        return cls(
            rlm_child_id=require_str(payload, "rlm_child_id", what="ChildResultView"),
            session_name=optional_str(payload, "session_name", what="ChildResultView"),
            session_dir=optional_str(payload, "session_dir", what="ChildResultView"),
            status=status,
            settled=settled,
            answer_preview=optional_str(
                payload, "answer_preview", what="ChildResultView"
            ),
            error=optional_str(payload, "error", what="ChildResultView"),
            duration_ms=payload.get("duration_ms"),
            tool_use_count=payload.get("tool_use_count"),
            replied_since_task=payload.get("replied_since_task"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ListSubagentsRequest:
    """The (fieldless) typed gate for the list operation.

    Carries only the schema version so an explicit future version or an
    unknown field is a strict typed error instead of silent acceptance.
    """

    @classmethod
    def from_dict(cls, raw: Any) -> ListSubagentsRequest:
        payload = require_payload(raw, what="ListSubagentsRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ListSubagentsRequest")
        reject_unknown(payload, _LIST_SUBAGENTS_FIELDS, what="ListSubagentsRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


class RlmConnector:
    """The typed boundary over an ``RlmHost`` (or ``NoRlmHost``)."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def spawn(self, request: SpawnRequest) -> dict:
        handle = self._host.spawn(
            request.prompt,
            name=request.name,
            model=request.model,
            thinking=request.thinking,
        )
        return {
            "rlm_child_id": handle.rlm_child_id,
            "name": handle.name,
            "session_dir": str(handle.session_dir),
            "model": handle.model,
        }

    def collect(self, request: CollectRequest) -> dict:
        results = self._host.collect(request.targets, timeout_ms=request.timeout_ms)
        return {"results": [ChildResultView.from_result(r).to_dict() for r in results]}

    def list_subagents(self) -> dict:
        return {"subagents": [_subagent_view(s) for s in self._host.list_subagents()]}

    def progress_note(self, request: ProgressNoteRequest) -> dict:
        result = self._host.progress_note(request.child_id, request.message)
        return {"accepted": result.accepted, "retry_after_ms": result.retry_after_ms}

    def create_session(
        self, request: CreateSessionRequest, *, session_store: Any = None
    ) -> dict:
        handle = self._host.create_session(
            request.prompt,
            name=request.name,
            model=request.model,
            thinking=request.thinking,
            session_store=session_store,
        )
        return {
            "active_session_id": handle.active_session_id,
            "session_id": handle.session_id,
            "name": handle.name,
            "session_file": str(handle.session_file),
            "model": handle.model,
        }

    def delete_subagent(self, request: DeleteRequest) -> dict:
        return dict(self._host.delete_subagent(request.target))

    def rename(self, request: RenameRequest) -> dict:
        return dict(self._host.rename(request.target, request.name))


def _subagent_view(subagent: RLMSubagent) -> dict:
    if subagent.status not in SUBAGENT_STATUSES:
        raise PrimeError(
            "bad_value", f"subagent status {subagent.status!r} not in SUBAGENT_STATUSES"
        )
    activity = subagent.activity
    if activity is not None and activity.kind not in ACTIVITY_KINDS:
        raise PrimeError(
            "bad_value", f"activity kind {activity.kind!r} not in ACTIVITY_KINDS"
        )
    # Session identity rides the typed view (RLM-03): the durable child
    # session hex once the host populates it, None on rows predating the
    # durability cutover. ``answer_preview`` stays off this channel —
    # parent answer content is visible only through collect (RLM-04).
    return {
        "rlm_child_id": subagent.rlm_child_id,
        "session_name": subagent.session_name,
        "session_dir": str(subagent.session_dir),
        "status": subagent.status,
        "activity": None
        if activity is None
        else {"kind": activity.kind, "tool_name": activity.tool_name},
        "progress_note": subagent.progress_note,
        "session_id": getattr(subagent, "session_id", None),
        "active_session_id": getattr(subagent, "active_session_id", None),
    }


__all__ = [
    "SCHEMA_VERSION",
    "ChildResultView",
    "CollectRequest",
    "CreateSessionRequest",
    "DeleteRequest",
    "ListSubagentsRequest",
    "ProgressNoteRequest",
    "RenameRequest",
    "RlmConnector",
    "SpawnRequest",
]
