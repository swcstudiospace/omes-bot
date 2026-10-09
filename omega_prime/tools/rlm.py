# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the RLM recursion tool family on one registry, bound to one parent agent.

Ported from Prime Agent's kernel RLM API (see ``omega_prime/agent/rlm.py``).
Registration is gated on the ``prime.rlm.enabled`` config flag (default off);
when disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from omega_prime.agent.rlm import host_for, require_parent
from omega_prime.prime.rlm import (
    CollectRequest,
    CreateSessionRequest,
    DeleteRequest,
    ListSubagentsRequest,
    ProgressNoteRequest,
    RenameRequest,
    RlmConnector,
    SpawnRequest,
)
from omega_prime.prime.types import reject_extra
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


def register_rlm_tools(
    registry: ToolRegistry,
    parent: Any,
    *,
    enabled: bool = True,
    run_child: Any = None,
    session_store: Any = None,
) -> list[str]:
    """Register the RLM family. ``enabled=False`` registers nothing (LOOP-05).

    A non-``None`` ``parent`` must satisfy the RLM parent contract; a
    misconfigured parent fails here, not at the first model call. A ``None``
    parent registers the tools without ever constructing a host (catalog path).
    """
    if not enabled:
        return []
    if parent is not None:
        require_parent(parent)

    def connector() -> RlmConnector:
        return RlmConnector(host_for(parent, True, run_child=run_child))

    # Every handler rejects undeclared arguments, then decodes only its
    # declared parameters through the typed/versioned request boundary before
    # touching the host (CONN-01). Required parameters default to ``None`` so
    # an omitted field reaches the typed decoder (``bad_type``) instead of a
    # Python ``TypeError``. Handlers never catch ``PrimeError``:
    # ``ToolRegistry.dispatch`` converts it into the typed error envelope and
    # audits it as an error. Policy and approval already ran before this
    # handler. Tool result envelopes are unchanged.

    def rlm_spawn(
        prompt: Any = None,
        name: Any = None,
        model: str | None = None,
        thinking: str | None = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="rlm_spawn")
        request = SpawnRequest.from_dict(
            {
                "prompt": prompt,
                "name": name,
                "model": model,
                "thinking": thinking,
                "schema_version": schema_version,
            }
        )
        return connector().spawn(request)

    def rlm_collect(
        targets: Any = None,
        timeout_ms: int = 0,
        schema_version: int | None = None,
        **extra: Any,
    ) -> list:
        reject_extra(extra, what="rlm_collect")
        request = CollectRequest.from_dict(
            {
                "targets": targets,
                "timeout_ms": timeout_ms,
                "schema_version": schema_version,
            }
        )
        return connector().collect(request)["results"]

    def rlm_list_subagents(schema_version: int | None = None, **extra: Any) -> list:
        reject_extra(extra, what="rlm_list_subagents")
        ListSubagentsRequest.from_dict({"schema_version": schema_version})
        return connector().list_subagents()["subagents"]

    def rlm_delete_subagent(
        target: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="rlm_delete_subagent")
        request = DeleteRequest.from_dict(
            {"target": target, "schema_version": schema_version}
        )
        return connector().delete_subagent(request)

    def rlm_create_session(
        prompt: Any = None,
        name: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        # ``cwd`` is not declared: a per-session directory is unsupported, so a
        # model-supplied ``cwd`` reaches ``reject_extra`` as an unknown field.
        reject_extra(extra, what="rlm_create_session")
        request = CreateSessionRequest.from_dict(
            {
                "prompt": prompt,
                "name": name,
                "model": model,
                "thinking": thinking,
                "schema_version": schema_version,
            }
        )
        return connector().create_session(request, session_store=session_store)

    def rlm_progress_note(
        child_id: Any = None,
        message: Any = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="rlm_progress_note")
        request = ProgressNoteRequest.from_dict(
            {
                "child_id": child_id,
                "message": message,
                "schema_version": schema_version,
            }
        )
        return connector().progress_note(request)

    def rlm_rename(
        target: Any = None,
        name: Any = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="rlm_rename")
        request = RenameRequest.from_dict(
            {"target": target, "name": name, "schema_version": schema_version}
        )
        return connector().rename(request)

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
