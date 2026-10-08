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
            name=require_str(payload, "name", what="SpawnRequest"),
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
        if targets is not None and not isinstance(targets, (str, list)):
            raise PrimeError(
                "bad_type", "CollectRequest.targets must be a string, list, or null"
            )
        if isinstance(targets, list) and not all(isinstance(t, str) for t in targets):
            raise PrimeError(
                "bad_type", "CollectRequest.targets entries must be strings"
            )
        return cls(
            targets=targets,
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
    return {
        "rlm_child_id": subagent.rlm_child_id,
        "session_name": subagent.session_name,
        "session_dir": str(subagent.session_dir),
        "status": subagent.status,
        "activity": None
        if activity is None
        else {"kind": activity.kind, "tool_name": activity.tool_name},
        "progress_note": subagent.progress_note,
    }


__all__ = [
    "SCHEMA_VERSION",
    "ChildResultView",
    "CollectRequest",
    "ProgressNoteRequest",
    "RlmConnector",
    "SpawnRequest",
]
