# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over the Prime heartbeat runtime (CONN-01).

Sits between the ``heartbeat_*`` tool handlers and
``omega_prime/cron/heartbeat_runtime.py`` (``HeartbeatRuntime``). Every
request is decoded through a versioned, strict request type before the runtime
is touched: an unknown field, a future ``schema_version`` or a malformed value
is a typed ``PrimeError`` with no side effect. Result envelopes are the
runtime's own.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from typing import Any

from omega_prime.cron.heartbeat_runtime import HeartbeatRuntime
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    reject_unknown,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_SET_FIELDS = frozenset(
    {"schema_version", "session", "prompt", "interval_seconds", "due_at"}
)
_CLEAR_FIELDS = frozenset({"schema_version", "job_id"})
_LIST_FIELDS = frozenset({"schema_version"})


def _finite_number(
    payload: dict, key: str, *, what: str, positive: bool = False
) -> int | float:
    """A finite JSON number; booleans and strings are never numbers."""
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PrimeError("bad_type", f"{what}.{key} must be a number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise PrimeError("bad_value", f"{what}.{key} must be finite")
    if positive and value <= 0:
        raise PrimeError("bad_value", f"{what}.{key} must be > 0")
    return value


@dataclass(frozen=True)
class SetRequest:
    session: str
    prompt: str
    interval_seconds: int | float
    due_at: int | float | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> SetRequest:
        payload = require_payload(raw, what="SetRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="SetRequest")
        reject_unknown(payload, _SET_FIELDS, what="SetRequest")
        session = require_str(payload, "session", what="SetRequest")
        if not session.strip():
            raise PrimeError("bad_type", "SetRequest.session must not be blank")
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            raise PrimeError("bad_type", "SetRequest.prompt must be a string")
        due_at = (
            None
            if payload.get("due_at") is None
            else _finite_number(payload, "due_at", what="SetRequest")
        )
        return cls(
            session=session,
            prompt=prompt,
            interval_seconds=_finite_number(
                payload, "interval_seconds", what="SetRequest", positive=True
            ),
            due_at=due_at,
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ClearRequest:
    job_id: str

    @classmethod
    def from_dict(cls, raw: Any) -> ClearRequest:
        payload = require_payload(raw, what="ClearRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ClearRequest")
        reject_unknown(payload, _CLEAR_FIELDS, what="ClearRequest")
        return cls(job_id=require_str(payload, "job_id", what="ClearRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class ListRequest:
    """Typed gate for heartbeat_list (version + unknown-field strictness only)."""

    @classmethod
    def from_dict(cls, raw: Any) -> ListRequest:
        payload = require_payload(raw, what="ListRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="ListRequest")
        reject_unknown(payload, _LIST_FIELDS, what="ListRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


class HeartbeatConnector:
    """The typed boundary over one ``HeartbeatRuntime``."""

    def __init__(self, runtime: HeartbeatRuntime) -> None:
        self._runtime = runtime

    def schedule(self, request: SetRequest) -> dict:
        due_at = time.time() if request.due_at is None else request.due_at
        try:
            job_id = self._runtime.schedule(
                request.session,
                request.prompt,
                interval_seconds=request.interval_seconds,
                due_at=due_at,
            )
        except ValueError as exc:
            # Values strict decoding cannot know: the scheduler calendar limits.
            raise PrimeError("bad_value", str(exc)) from exc
        return {"scheduled": job_id, "session": request.session}

    def list_jobs(self, request: ListRequest) -> list:
        return self._runtime.list_jobs()

    def clear(self, request: ClearRequest) -> dict:
        return self._runtime.clear(request.job_id)


__all__ = [
    "SCHEMA_VERSION",
    "ClearRequest",
    "HeartbeatConnector",
    "ListRequest",
    "SetRequest",
]
