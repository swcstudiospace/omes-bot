# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the goals tool family on one registry.

Ported from Prime Agent's goals (see ``omega_prime/agent/goals.py``). Gated on
the ``prime.goals.enabled`` config flag (default off); when disabled the family
is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.agent.goals import PrimeGoalStore
from omega_prime.prime.goals import (
    ClearRequest,
    GoalsConnector,
    PauseRequest,
    ResumeRequest,
    SetGoalRequest,
    StatusRequest,
)
from omega_prime.prime.types import reject_extra
from omega_prime.tools.registry import ToolRegistry

# Offered after the harness tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
GOAL_TOOL_NAMES = (
    "goal_set",
    "goal_pause",
    "goal_resume",
    "goal_clear",
    "goal_status",
)

_WRITE_TOOLS = frozenset({"goal_set", "goal_pause", "goal_resume", "goal_clear"})


def register_goal_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
) -> list[str]:
    """Register the goals family. ``enabled=False`` registers nothing (LOOP-05)."""
    if not enabled:
        registry.runtime_bindings.pop("prime_goals", None)
        return []

    def store() -> PrimeGoalStore:
        return PrimeGoalStore(Path(root) / "goals")

    # The loop reloads through this factory at every boundary, so dispatched
    # and external writes are immediately authoritative. Never a cached store.
    registry.runtime_bindings["prime_goals"] = store

    def connector() -> GoalsConnector:
        return GoalsConnector(Path(root) / "goals")

    # Every handler rejects undeclared arguments, then decodes through the
    # typed/versioned request boundary before touching the store (CONN-01).
    # A malformed budget/steps payload, an explicit future version, or an
    # unknown field raises a PrimeError that ``registry.dispatch`` turns into
    # the structured error envelope (audited as ``error``) with no side
    # effect; the live ``prime_goals`` factory binding is unchanged, and
    # registry policy/approval already ran. Result envelopes are unchanged.

    def goal_set(
        objective: Any = None,
        token_budget: int | None = None,
        steps: list | None = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="goal_set")
        request = SetGoalRequest.from_dict(
            {
                "objective": objective,
                "token_budget": token_budget,
                "steps": [] if steps is None else steps,
                "schema_version": schema_version,
            }
        )
        return connector().set_goal(request)

    def goal_pause(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="goal_pause")
        request = PauseRequest.from_dict({"schema_version": schema_version})
        return connector().pause(request)

    def goal_resume(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="goal_resume")
        request = ResumeRequest.from_dict({"schema_version": schema_version})
        return connector().resume(request)

    def goal_clear(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="goal_clear")
        request = ClearRequest.from_dict({"schema_version": schema_version})
        return connector().clear(request)

    def goal_status(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="goal_status")
        request = StatusRequest.from_dict({"schema_version": schema_version})
        return connector().status(request)

    handlers: dict[str, Callable[..., Any]] = {
        "goal_set": goal_set,
        "goal_pause": goal_pause,
        "goal_resume": goal_resume,
        "goal_clear": goal_clear,
        "goal_status": goal_status,
    }
    if tuple(handlers) != GOAL_TOOL_NAMES:
        raise RuntimeError("goal tool handlers drifted from GOAL_TOOL_NAMES")
    for name in GOAL_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(GOAL_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "goal_set": (
        "Set a persistent goal (objective + optional steps and token budget). "
        "The goal persists across turns until completed, paused, or cleared.",
        _object(
            {
                "objective": _string("The goal objective."),
                "token_budget": {
                    "type": "integer",
                    "description": "Optional token budget; accrual stops the loop at the cap.",
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional ordered steps.",
                },
            },
            ["objective"],
        ),
    ),
    "goal_pause": ("Pause the active goal.", _object({}, [])),
    "goal_resume": ("Resume a paused goal.", _object({}, [])),
    "goal_clear": ("Clear the goal and its steps.", _object({}, [])),
    "goal_status": (
        "Read the goal's objective, steps, budget accrual, and stale state.",
        _object({}, []),
    ),
}

__all__ = ["GOAL_TOOL_NAMES", "register_goal_tools"]
