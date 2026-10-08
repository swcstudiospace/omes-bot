# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the RLM recursion tool family on one registry, bound to one parent agent.

Ported from Prime Agent's kernel RLM API (see ``omega_prime/agent/rlm.py``).
Registration is gated on the ``prime.rlm.enabled`` config flag (default off);
when disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from omega_prime.agent.rlm import host_for
from omega_prime.tools.registry import ToolRegistry

# Offered after the substrate tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
RLM_TOOL_NAMES = (
    "rlm_spawn",
    "rlm_collect",
    "rlm_list_subagents",
    "rlm_delete_subagent",
    "rlm_create_session",
    "rlm_progress_note",
    "rlm_rename",
)

_WRITE_TOOLS = frozenset(
    {"rlm_spawn", "rlm_create_session", "rlm_delete_subagent", "rlm_rename"}
)


def _jsonable(value: Any) -> Any:
    """Dataclass → JSON-safe dict, preserving the Prime field names."""
    if hasattr(value, "__dataclass_fields__"):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def register_rlm_tools(
    registry: ToolRegistry,
    parent: Any,
    *,
    enabled: bool = True,
    run_child: Any = None,
    session_store: Any = None,
) -> list[str]:
    """Register the RLM family. ``enabled=False`` registers nothing (LOOP-05)."""
    if not enabled:
        return []

    def host() -> Any:
        return host_for(parent, True, run_child=run_child)

    def rlm_spawn(
        prompt: str,
        name: str,
        model: str | None = None,
        thinking: str | None = None,
    ) -> dict:
        return _jsonable(
            host().spawn(prompt, name=name, model=model, thinking=thinking)
        )

    def rlm_collect(targets: Any = None, timeout_ms: int = 0) -> list:
        return _jsonable(host().collect(targets, timeout_ms=timeout_ms))

    def rlm_list_subagents() -> list:
        return _jsonable(host().list_subagents())

    def rlm_delete_subagent(target: Any) -> dict:
        return _jsonable(host().delete_subagent(target))

    def rlm_create_session(
        prompt: str,
        name: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        cwd: str | None = None,
    ) -> dict:
        return _jsonable(
            host().create_session(
                prompt,
                name=name,
                model=model,
                thinking=thinking,
                cwd=cwd,
                session_store=session_store,
            )
        )

    def rlm_progress_note(child_id: str, message: str) -> dict:
        return _jsonable(host().progress_note(child_id, message))

    def rlm_rename(target: Any, name: str) -> dict:
        return _jsonable(host().rename(target, name))

    handlers: dict[str, Callable[..., Any]] = {
        "rlm_spawn": rlm_spawn,
        "rlm_collect": rlm_collect,
        "rlm_list_subagents": rlm_list_subagents,
        "rlm_delete_subagent": rlm_delete_subagent,
        "rlm_create_session": rlm_create_session,
        "rlm_progress_note": rlm_progress_note,
        "rlm_rename": rlm_rename,
    }
    if tuple(handlers) != RLM_TOOL_NAMES:
        raise RuntimeError("rlm tool handlers drifted from RLM_TOOL_NAMES")
    for name in RLM_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(RLM_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "rlm_spawn": (
        "Spawn a recursive child agent and return once its task is admitted. "
        "name is required and must be unique among siblings. Returns a handle "
        "with rlm_child_id; collect results with rlm_collect.",
        _object(
            {
                "prompt": _string("The child agent's task."),
                "name": _string("Unique sibling name for the child."),
                "model": _string("Optional provider/model selector."),
                "thinking": _string("Optional reasoning level (off/low/medium/high)."),
            },
            ["prompt", "name"],
        ),
    ),
    "rlm_collect": (
        "Collect typed results from direct RLM children. targets selects "
        "children (handle, subagent row, name, or a mixed list); omitted "
        "selects all direct children not being deleted. timeout_ms=0 is a "
        "non-blocking snapshot; a positive timeout returns current snapshots "
        "on elapse and never errors.",
        _object(
            {
                "targets": {
                    "description": "Handle, name, or list. Omit for all children."
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": "Wait budget; 0 = snapshot.",
                },
            },
            [],
        ),
    ),
    "rlm_list_subagents": (
        "List direct RLM children retained by the current parent session.",
        _object({}, []),
    ),
    "rlm_delete_subagent": (
        "Reap one direct RLM child and drop its retained result.",
        _object({"target": _string("Child name or rlm_child_id.")}, ["target"]),
    ),
    "rlm_create_session": (
        "Create and prompt a durable named session that survives this turn.",
        _object(
            {
                "prompt": _string("The session's initial task."),
                "name": _string("Optional session name."),
                "model": _string("Optional provider/model selector."),
                "thinking": _string("Optional reasoning level."),
                "cwd": _string("Optional working directory."),
            },
            ["prompt"],
        ),
    ),
    "rlm_progress_note": (
        "Record a progress note on a child (max 512 UTF-16 code units, "
        "throttled to about one per 10s; a throttled note returns "
        "accepted=false with retry_after_ms and never errors).",
        _object(
            {
                "child_id": _string("The child's rlm_child_id."),
                "message": _string("The progress note."),
            },
            ["child_id", "message"],
        ),
    ),
    "rlm_rename": (
        "Rename this session (target 'self') or one direct child.",
        _object(
            {
                "target": _string("'self', a child name, or an rlm_child_id."),
                "name": _string("The new name."),
            },
            ["target", "name"],
        ),
    ),
}


__all__ = ["RLM_TOOL_NAMES", "register_rlm_tools"]
