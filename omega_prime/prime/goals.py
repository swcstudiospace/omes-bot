# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over the Prime goals port (CONN-01).

Sits between the ``goal_*`` tool handlers and
``omega_prime/agent/goals.py`` (``PrimeGoalStore``). The status vocabulary
is the closed Prime set; budget arithmetic rides
``goal_token_delta_for_usage``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omega_prime.agent.goals import STATUSES, PrimeGoalStore
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    optional_int,
    reject_unknown,
    require_member,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_SET_FIELDS = frozenset(
    {"schema_version", "objective", "token_budget", "stale_after_turns", "steps"}
)
_ACCRUE_FIELDS = frozenset({"schema_version", "usage"})
_PAUSE_FIELDS = frozenset({"schema_version"})
_RESUME_FIELDS = frozenset({"schema_version"})
_CLEAR_FIELDS = frozenset({"schema_version"})
_STATUS_FIELDS = frozenset({"schema_version"})


@dataclass(frozen=True)
class SetGoalRequest:
    objective: str
    token_budget: int | None = None
    stale_after_turns: int | None = None
    steps: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Any) -> SetGoalRequest:
        payload = require_payload(raw, what="SetGoalRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="SetGoalRequest")
        reject_unknown(payload, _SET_FIELDS, what="SetGoalRequest")
        steps = payload.get("steps", [])
        if not isinstance(steps, list) or not all(isinstance(s, str) for s in steps):
            raise PrimeError(
                "bad_type", "SetGoalRequest.steps must be a list of strings"
            )
        if any(not step.strip() for step in steps):
            raise PrimeError(
                "bad_value", "SetGoalRequest.steps must not contain blank steps"
            )
        objective = require_str(payload, "objective", what="SetGoalRequest")
        if not objective.strip():
            raise PrimeError("bad_value", "SetGoalRequest.objective must not be blank")
        return cls(
            objective=objective,
            token_budget=optional_int(payload, "token_budget", what="SetGoalRequest"),
            stale_after_turns=optional_int(
                payload, "stale_after_turns", what="SetGoalRequest"
            ),
            steps=tuple(steps),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class AccrueRequest:
    usage: dict

    @classmethod
    def from_dict(cls, raw: Any) -> AccrueRequest:
        payload = require_payload(raw, what="AccrueRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="AccrueRequest")
        reject_unknown(payload, _ACCRUE_FIELDS, what="AccrueRequest")
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            raise PrimeError("bad_type", "AccrueRequest.usage must be an object")
        return cls(usage=usage)

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class GoalStatusView:
    """The Prime goal status, with the closed status vocabulary enforced."""

    objective: str
    prime_status: str
    tokens_used: int
    token_budget: int | None
    budget_exhausted: bool
    stale: bool

    @classmethod
    def from_status(cls, status: dict) -> GoalStatusView:
        prime_status = status.get("prime_status")
        if prime_status not in STATUSES and prime_status != "cleared":
            raise PrimeError(
                "bad_value", f"prime_status {prime_status!r} not in STATUSES"
            )
        return cls(
            objective=status.get("objective", ""),
            prime_status=prime_status,
            tokens_used=status.get("tokens_used", 0),
            token_budget=status.get("token_budget"),
            budget_exhausted=bool(status.get("budget_exhausted")),
            stale=bool(status.get("stale")),
        )

    @classmethod
    def from_dict(cls, raw: Any) -> GoalStatusView:
        payload = require_payload(raw, what="GoalStatusView")
        return cls(
            objective=require_str(payload, "objective", what="GoalStatusView"),
            prime_status=require_member(
                payload, "prime_status", (*STATUSES, "cleared"), what="GoalStatusView"
            ),
            tokens_used=payload.get("tokens_used", 0),
            token_budget=payload.get("token_budget"),
            budget_exhausted=bool(payload.get("budget_exhausted")),
            stale=bool(payload.get("stale")),
        )

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_request(raw: Any, *, fields: frozenset, what: str) -> dict:
    """Validate a fieldless lifecycle payload: version gate + no unknowns."""
    payload = require_payload(raw, what=what)
    check_schema_version(payload, SCHEMA_VERSION, what=what)
    reject_unknown(payload, fields, what=what)
    return payload


@dataclass(frozen=True)
class PauseRequest:
    """Typed gate for goal_pause (version + unknown-field strictness only)."""

    @classmethod
    def from_dict(cls, raw: Any) -> PauseRequest:
        _empty_request(raw, fields=_PAUSE_FIELDS, what="PauseRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class ResumeRequest:
    """Typed gate for goal_resume (version + unknown-field strictness only)."""

    @classmethod
    def from_dict(cls, raw: Any) -> ResumeRequest:
        _empty_request(raw, fields=_RESUME_FIELDS, what="ResumeRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class ClearRequest:
    """Typed gate for goal_clear (version + unknown-field strictness only)."""

    @classmethod
    def from_dict(cls, raw: Any) -> ClearRequest:
        _empty_request(raw, fields=_CLEAR_FIELDS, what="ClearRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class StatusRequest:
    """Typed gate for goal_status (version + unknown-field strictness only)."""

    @classmethod
    def from_dict(cls, raw: Any) -> StatusRequest:
        _empty_request(raw, fields=_STATUS_FIELDS, what="StatusRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


class GoalsConnector:
    """The typed boundary over ``PrimeGoalStore`` (one store per directory)."""

    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)

    def _store(self) -> PrimeGoalStore:
        return PrimeGoalStore(self._directory)

    def set_goal(self, request: SetGoalRequest) -> dict:
        kwargs: dict[str, Any] = {"token_budget": request.token_budget}
        if request.stale_after_turns is not None:
            kwargs["stale_after_turns"] = request.stale_after_turns
        return self._store().replace_goal(
            request.objective, list(request.steps), **kwargs
        )

    def accrue(self, request: AccrueRequest) -> dict:
        return self._store().accrue_turn(request.usage)

    def status(self, request: StatusRequest) -> dict:
        raw = self._store().prime_status()
        GoalStatusView.from_status(raw)
        return raw

    def pause(self, request: PauseRequest) -> dict:
        raw = self._store().pause()
        GoalStatusView.from_status(raw)
        return raw

    def resume(self, request: ResumeRequest) -> dict:
        raw = self._store().resume()
        GoalStatusView.from_status(raw)
        return raw

    def clear(self, request: ClearRequest) -> dict:
        raw = self._store().clear()
        GoalStatusView.from_status(raw)
        return raw

    def continuation_prompt(self) -> dict:
        return {"prompt": self._store().continuation_prompt()}


__all__ = [
    "SCHEMA_VERSION",
    "AccrueRequest",
    "ClearRequest",
    "GoalStatusView",
    "GoalsConnector",
    "PauseRequest",
    "ResumeRequest",
    "SetGoalRequest",
    "StatusRequest",
]
