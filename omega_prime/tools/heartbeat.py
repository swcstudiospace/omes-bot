# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the heartbeat tool family on one registry.

Ported from Prime Agent's heartbeat (see ``omega_prime/cron/heartbeat.py``).
Gated on the ``prime.heartbeat.enabled`` config flag (default off); when
disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.cron.heartbeat import (
    clear_heartbeat,
    list_heartbeats,
    schedule_heartbeat,
)
from omega_prime.cron.scheduler import JobStore
from omega_prime.tools.registry import ToolRegistry

# Offered after the goals tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
HEARTBEAT_TOOL_NAMES = (
    "heartbeat_set",
    "heartbeat_list",
    "heartbeat_clear",
)

_WRITE_TOOLS = frozenset({"heartbeat_set", "heartbeat_clear"})


def register_heartbeat_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
) -> list[str]:
    """Register the heartbeat family. ``enabled=False`` registers nothing."""
    if not enabled:
        return []

    def store() -> JobStore:
        return JobStore(Path(root) / "cron" / "jobs.json")

    def heartbeat_set(
        session: str,
        prompt: str,
        interval_seconds: float,
        due_at: float | None = None,
    ) -> dict:
        job_id = schedule_heartbeat(
            store(),
            session,
            prompt,
            interval_seconds=interval_seconds,
            due_at=time.time() if due_at is None else due_at,
        )
        return {"scheduled": job_id, "session": session}

    def heartbeat_list() -> list:
        return list_heartbeats(store())

    def heartbeat_clear(job_id: str) -> dict:
        return clear_heartbeat(store(), job_id)

    handlers: dict[str, Callable[..., Any]] = {
        "heartbeat_set": heartbeat_set,
        "heartbeat_list": heartbeat_list,
        "heartbeat_clear": heartbeat_clear,
    }
    if tuple(handlers) != HEARTBEAT_TOOL_NAMES:
        raise RuntimeError("heartbeat tool handlers drifted from HEARTBEAT_TOOL_NAMES")
    for name in HEARTBEAT_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(HEARTBEAT_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "heartbeat_set": (
        "Schedule a recurring heartbeat that re-enters a named session with a "
        "prompt on an interval.",
        _object(
            {
                "session": _string("The named session to re-enter."),
                "prompt": _string("The prompt delivered each beat."),
                "interval_seconds": {
                    "type": "number",
                    "description": "Seconds between beats.",
                },
                "due_at": {
                    "type": "number",
                    "description": "First fire time (unix seconds); defaults to now.",
                },
            },
            ["session", "prompt", "interval_seconds"],
        ),
    ),
    "heartbeat_list": ("List all heartbeat jobs.", _object({}, [])),
    "heartbeat_clear": (
        "Remove one heartbeat by job id.",
        _object({"job_id": _string("The heartbeat job id.")}, ["job_id"]),
    ),
}

__all__ = ["HEARTBEAT_TOOL_NAMES", "register_heartbeat_tools"]
