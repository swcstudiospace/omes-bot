# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over bounded autonomous mode (CONN-01).

Sits between the ``autonomous_*`` tool handlers and
``omega_prime/agent/autonomous.py`` (``AutonomousDriver``). Stop reasons are
the closed Prime set; the honest-stop semantics are the capability module's
and pass through verbatim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omega_prime.agent.autonomous import (
    STOP_COMPLETED,
    STOP_GATE_FAILED,
    STOP_GATE_PASSED,
    STOP_MAX_MINUTES,
    STOP_MAX_TOKENS,
    STOP_MAX_TURNS,
    AutonomousBudget,
    AutonomousDriver,
)
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    optional_int,
    reject_unknown,
    require_member,
    require_payload,
)

SCHEMA_VERSION = 1

STOP_REASONS: tuple[str, ...] = (
    STOP_MAX_TURNS,
    STOP_MAX_TOKENS,
    STOP_MAX_MINUTES,
    STOP_GATE_PASSED,
    STOP_GATE_FAILED,
    STOP_COMPLETED,
)

_START_FIELDS = frozenset(
    {"schema_version", "max_turns", "max_tokens", "max_minutes", "gate", "gate_retries"}
)


@dataclass(frozen=True)
class StartRequest:
    max_turns: int | None = None
    max_tokens: int | None = None
    max_minutes: float | None = None
    gate: tuple[str, ...] | None = None
    gate_retries: int | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> StartRequest:
        payload = require_payload(raw, what="StartRequest")
        check_schema_version(payload, SCHEMA_VERSION, what="StartRequest")
        reject_unknown(payload, _START_FIELDS, what="StartRequest")
        gate = payload.get("gate")
        if gate is not None and (
            not isinstance(gate, list)
            or not gate
            or not all(isinstance(g, str) for g in gate)
        ):
            raise PrimeError(
                "bad_type",
                "StartRequest.gate must be a non-empty argv list or null",
            )
        max_minutes = payload.get("max_minutes")
        if max_minutes is not None and (
            isinstance(max_minutes, bool)
            or not isinstance(max_minutes, (int, float))
            or max_minutes <= 0
        ):
            raise PrimeError(
                "bad_value",
                "StartRequest.max_minutes must be a positive number or null",
            )
        return cls(
            max_turns=optional_int(payload, "max_turns", what="StartRequest"),
            max_tokens=optional_int(payload, "max_tokens", what="StartRequest"),
            max_minutes=max_minutes,
            gate=None if gate is None else tuple(gate),
            gate_retries=optional_int(
                payload, "gate_retries", what="StartRequest", minimum=0
            ),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "max_turns": self.max_turns,
            "max_tokens": self.max_tokens,
            "max_minutes": self.max_minutes,
            "gate": None if self.gate is None else list(self.gate),
            "gate_retries": self.gate_retries,
        }


@dataclass(frozen=True)
class VerdictView:
    """One driver verdict: ``continue`` with a prompt, or ``stop`` with a
    reason from the closed Prime set."""

    action: str
    reason: str | None = None
    prompt: str | None = None
    turns: int = 0
    tokens: int = 0

    @classmethod
    def from_verdict(cls, verdict: dict) -> VerdictView:
        action = verdict.get("action")
        if action not in ("continue", "stop"):
            raise PrimeError(
                "bad_value", f"verdict action {action!r} must be continue|stop"
            )
        reason = verdict.get("reason")
        if action == "stop" and reason not in STOP_REASONS:
            raise PrimeError("bad_value", f"stop reason {reason!r} not in STOP_REASONS")
        return cls(
            action=action,
            reason=reason,
            prompt=verdict.get("prompt"),
            turns=verdict.get("turns", 0),
            tokens=verdict.get("tokens", 0),
        )

    @classmethod
    def from_dict(cls, raw: Any) -> VerdictView:
        payload = require_payload(raw, what="VerdictView")
        action = require_member(
            payload, "action", ("continue", "stop"), what="VerdictView"
        )
        reason = payload.get("reason")
        if action == "stop":
            require_member(payload, "reason", STOP_REASONS, what="VerdictView")
        return cls(
            action=action,
            reason=reason,
            prompt=payload.get("prompt"),
            turns=payload.get("turns", 0),
            tokens=payload.get("tokens", 0),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class AutonomousConnector:
    """Builds and drives an ``AutonomousDriver`` from typed requests."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def start(self, request: StartRequest) -> AutonomousDriver:
        driver = AutonomousDriver(
            self._root,
            budget=AutonomousBudget(
                max_turns=request.max_turns,
                max_tokens=request.max_tokens,
                max_minutes=request.max_minutes,
            ),
            gate=None if request.gate is None else list(request.gate),
            gate_retries=1 if request.gate_retries is None else request.gate_retries,
        )
        driver.start()
        return driver

    def after_turn(self, driver: AutonomousDriver, result: dict) -> dict:
        return VerdictView.from_verdict(driver.after_turn(result)).to_dict()


__all__ = [
    "SCHEMA_VERSION",
    "STOP_REASONS",
    "AutonomousConnector",
    "StartRequest",
    "VerdictView",
]
