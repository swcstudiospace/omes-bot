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
        return []

    def store() -> PrimeGoalStore:
        return PrimeGoalStore(Path(root) / "goals")

    def goal_set(
        objective: str,
        token_budget: int | None = None,
        steps: list | None = None,
    ) -> dict:
        goal = store()
        result = goal.set_objective(objective, token_budget=token_budget)
        for step in steps or []:
            goal.add_step(str(step))
        return result

    def goal_pause() -> dict:
        return store().pause()

    def goal_resume() -> dict:
        return store().resume()

    def goal_clear() -> dict:
        return store().clear()

    def goal_status() -> dict:
        return store().prime_status()

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
