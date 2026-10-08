# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the autonomous-mode tool family on one registry.

Ported from Prime Agent's autonomous driver (see
``omega_prime/agent/autonomous.py``). Gated on the ``prime.autonomous.enabled``
config flag (default off); when disabled the family is absent from the registry
and roster (LOOP-05). The driver is held per-registry so start/status/stop share
one run.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.agent.autonomous import AutonomousBudget, AutonomousDriver
from omega_prime.tools.registry import ToolRegistry

# Offered after the heartbeat tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
AUTONOMOUS_TOOL_NAMES = (
    "autonomous_start",
    "autonomous_status",
    "autonomous_stop",
)

_WRITE_TOOLS = frozenset({"autonomous_start", "autonomous_stop"})


def register_autonomous_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
    config: dict | None = None,
) -> list[str]:
    """Register the autonomous family. ``enabled=False`` registers nothing.

    ``config`` is the ``prime.autonomous`` subtree (max_turns / max_tokens /
    max_minutes / gate); values may be overridden per ``autonomous_start`` call.
    """
    if not enabled:
        return []

    config = config or {}
    state: dict[str, AutonomousDriver | None] = {"driver": None}

    def autonomous_start(
        max_turns: int | None = None,
        max_tokens: int | None = None,
        max_minutes: float | None = None,
        gate: list | None = None,
        gate_retries: int | None = None,
    ) -> dict:
        budget = AutonomousBudget(
            max_turns=max_turns if max_turns is not None else config.get("max_turns"),
            max_tokens=max_tokens
            if max_tokens is not None
            else config.get("max_tokens"),
            max_minutes=(
                max_minutes if max_minutes is not None else config.get("max_minutes")
            ),
        )
        driver = AutonomousDriver(
            root=Path(root),
            budget=budget,
            gate=gate if gate is not None else config.get("gate"),
            gate_retries=(
                gate_retries
                if gate_retries is not None
                else config.get("gate_retries", 1)
            ),
        )
        driver.start()
        state["driver"] = driver
        return {"started": True, "budget": driver.status()["budget"]}

    def autonomous_status() -> dict:
        driver = state["driver"]
        if driver is None:
            return {"running": False, "stopped": None}
        return driver.status()

    def autonomous_stop() -> dict:
        driver = state["driver"]
        state["driver"] = None
        return {"stopped": True, "was_running": bool(driver and driver.running)}

    handlers: dict[str, Callable[..., Any]] = {
        "autonomous_start": autonomous_start,
        "autonomous_status": autonomous_status,
        "autonomous_stop": autonomous_stop,
    }
    if tuple(handlers) != AUTONOMOUS_TOOL_NAMES:
        raise RuntimeError(
            "autonomous tool handlers drifted from AUTONOMOUS_TOOL_NAMES"
        )
    for name in AUTONOMOUS_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(AUTONOMOUS_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "autonomous_start": (
        "Start a bounded autonomous run: turn/token/minute budgets plus an "
        "optional quality gate (argv). Reaching a limit stops cleanly and does "
        "not imply task success.",
        _object(
            {
                "max_turns": {"type": "integer"},
                "max_tokens": {"type": "integer"},
                "max_minutes": {"type": "number"},
                "gate": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Quality gate argv run after each turn.",
                },
                "gate_retries": {"type": "integer"},
            },
            [],
        ),
    ),
    "autonomous_status": (
        "Read the current autonomous run's budget usage and stop state.",
        _object({}, []),
    ),
    "autonomous_stop": ("Stop the current autonomous run.", _object({}, [])),
}

__all__ = ["AUTONOMOUS_TOOL_NAMES", "register_autonomous_tools"]
