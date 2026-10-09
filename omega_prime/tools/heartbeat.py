# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the heartbeat tool family on one registry.

Ported from Prime Agent's heartbeat (see ``omega_prime/cron/heartbeat.py``).
Gated on the ``prime.heartbeat.enabled`` config flag (default off); when
disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.cron.heartbeat_runtime import HeartbeatRuntime
from omega_prime.prime.heartbeat import (
    ClearRequest,
    HeartbeatConnector,
    ListRequest,
    SetRequest,
)
from omega_prime.prime.types import reject_extra
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
        stale = registry.runtime_bindings.get("prime_heartbeat")
        if isinstance(stale, HeartbeatRuntime):
            stale.close()
            registry.runtime_bindings.pop("prime_heartbeat")
        return []

    path = Path(root, "cron", "jobs.json").expanduser().resolve()
    bindings = registry.runtime_bindings
    existing = bindings.get("prime_heartbeat")
    if isinstance(existing, HeartbeatRuntime) and existing.path == path:
        runtime = existing
    else:
        if isinstance(existing, HeartbeatRuntime):
            existing.close()
        runtime = HeartbeatRuntime(path)
        bindings["prime_heartbeat"] = runtime

    connector = HeartbeatConnector(runtime)

    # Every handler decodes through the typed/versioned request boundary
    # before touching the runtime (CONN-01). ``**extra`` only exists so an
    # undeclared argument reaches a typed ``unknown_field`` error after policy
    # and approval ran; it is never merged into the decoded payload. Result
    # envelopes are the runtime's own.

    def heartbeat_set(
        session: Any = None,
        prompt: Any = None,
        interval_seconds: Any = None,
        due_at: Any = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="heartbeat_set")
        request = SetRequest.from_dict(
            {
                "session": session,
                "prompt": prompt,
                "interval_seconds": interval_seconds,
                "due_at": due_at,
                "schema_version": schema_version,
            }
        )
        return connector.schedule(request)

    def heartbeat_list(schema_version: int | None = None, **extra: Any) -> list:
        reject_extra(extra, what="heartbeat_list")
        request = ListRequest.from_dict({"schema_version": schema_version})
        return connector.list_jobs(request)

    def heartbeat_clear(
        job_id: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="heartbeat_clear")
        request = ClearRequest.from_dict(
            {"job_id": job_id, "schema_version": schema_version}
        )
        return connector.clear(request)

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
