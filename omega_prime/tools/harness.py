"""Register the continual-harness tool family on one registry.

Ported from Prime Agent's harness CRUD + /refine (see
``omega_prime/learning/harness.py`` and ``omega_prime/agent/refine.py``).
Gated on the ``prime.harness.enabled`` config flag (default off); when
disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from omega_prime.agent.refine import refine
from omega_prime.learning.harness import HarnessKind, HarnessState
from omega_prime.tools.registry import ToolRegistry

# Offered after the RLM tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
HARNESS_TOOL_NAMES = (
    "harness_upsert",
    "harness_get",
    "harness_list",
    "harness_delete",
    "harness_refine",
    "harness_rollback",
)

_WRITE_TOOLS = frozenset(
    {"harness_upsert", "harness_delete", "harness_refine", "harness_rollback"}
)


def _state(root: Any, global_: bool) -> HarnessState:
    base = Path(root) / ("harness-global" if global_ else "harness-local")
    return HarnessState(base, scope="global" if global_ else "local").load()


def register_harness_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
) -> list[str]:
    """Register the harness family. ``enabled=False`` registers nothing."""
    if not enabled:
        return []

    def harness_upsert(
        kind: str,
        id: str,
        title: str,
        body: str,
        tags: list | None = None,
        global_: bool = False,
    ) -> dict:
        state = _state(root, global_)
        entry = state.upsert(
            cast(HarnessKind, kind), id, title=title, body=body, tags=tags
        )
        state.save()
        return asdict(entry)

    def harness_get(kind: str, id: str, global_: bool = False) -> dict:
        entry = _state(root, global_).get(cast(HarnessKind, kind), id)
        return asdict(entry) if entry else {"error": f"no {kind} entry {id!r}"}

    def harness_list(kind: str | None = None, global_: bool = False) -> list:
        narrowed = cast(HarnessKind, kind) if kind is not None else None
        return [asdict(e) for e in _state(root, global_).list_entries(narrowed)]

    def harness_delete(kind: str, id: str, global_: bool = False) -> dict:
        state = _state(root, global_)
        deleted = state.delete(cast(HarnessKind, kind), id)
        if deleted:
            state.save()
        return {"deleted": deleted, "id": id}

    def harness_refine(
        trigger: str,
        proposals: list,
        trajectory: Any,
        global_: bool = False,
    ) -> dict:
        state = _state(root, global_)
        result = refine(
            state, trigger=trigger, proposals=proposals, trajectory=trajectory
        )
        if result["applied"]:
            state.save()
        return result

    def harness_rollback(global_: bool = False) -> dict:
        state = _state(root, global_)
        restored = state.rollback()
        if restored:
            state.save()
        return {"restored": restored}

    handlers: dict[str, Callable[..., Any]] = {
        "harness_upsert": harness_upsert,
        "harness_get": harness_get,
        "harness_list": harness_list,
        "harness_delete": harness_delete,
        "harness_refine": harness_refine,
        "harness_rollback": harness_rollback,
    }
    if tuple(handlers) != HARNESS_TOOL_NAMES:
        raise RuntimeError("harness tool handlers drifted from HARNESS_TOOL_NAMES")
    for name in HARNESS_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(HARNESS_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_KIND = {"type": "string", "enum": ["prompt", "memory", "skill", "subagent", "factory"]}
_GLOBAL = {"type": "boolean", "description": "Use the cross-session global store."}

_SCHEMAS: dict[str, tuple[str, dict]] = {
    "harness_upsert": (
        "Create or update one supplemental harness entry (prompt note, memory, "
        "skill description, subagent spec, or factory spec). Session-local by "
        "default; global_=true writes the cross-session store.",
        _object(
            {
                "kind": _KIND,
                "id": _string("Stable entry id."),
                "title": _string("Entry title."),
                "body": _string("Entry body."),
                "tags": {"type": "array", "items": {"type": "string"}},
                "global_": _GLOBAL,
            },
            ["kind", "id", "title", "body"],
        ),
    ),
    "harness_get": (
        "Read one harness entry by kind and id.",
        _object(
            {"kind": _KIND, "id": _string("Entry id."), "global_": _GLOBAL},
            ["kind", "id"],
        ),
    ),
    "harness_list": (
        "List harness entries, optionally one kind.",
        _object({"kind": _KIND, "global_": _GLOBAL}, []),
    ),
    "harness_delete": (
        "Delete one harness entry.",
        _object(
            {"kind": _KIND, "id": _string("Entry id."), "global_": _GLOBAL},
            ["kind", "id"],
        ),
    ),
    "harness_refine": (
        "Review proposals against the current trajectory and apply only the "
        "evidence-backed ones. Every applied refinement is snapshotted for "
        "rollback; the base system prompt is never rewritten.",
        _object(
            {
                "trigger": _string("What triggered this refinement."),
                "proposals": {
                    "type": "array",
                    "description": "Each: kind, id, title, body, tags?, evidence (mandatory).",
                },
                "trajectory": {"description": "Messages or text the evidence cites."},
                "global_": _GLOBAL,
            },
            ["trigger", "proposals", "trajectory"],
        ),
    ),
    "harness_rollback": (
        "Restore the most recent pre-refinement snapshot exactly.",
        _object({"global_": _GLOBAL}, []),
    ),
}


__all__ = ["HARNESS_TOOL_NAMES", "register_harness_tools"]
