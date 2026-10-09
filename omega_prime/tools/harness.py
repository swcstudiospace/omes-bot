# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the continual-harness tool family on one registry.

Ported from Prime Agent's harness CRUD + /refine (see
``omega_prime/learning/harness.py`` and ``omega_prime/agent/refine.py``).
Gated on the ``prime.harness.enabled`` config flag (default off); when
disabled the family is absent from the registry and roster (LOOP-05).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from omega_prime.prime.errors import PrimeError
from omega_prime.prime.harness import (
    DeleteRequest,
    GetRequest,
    HarnessConnector,
    ListRequest,
    RefineRequest,
    RollbackRequest,
    UpsertRequest,
)
from omega_prime.prime.types import reject_extra
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

# Default for ``harness_refine``'s ``trajectory``: distinguishes an omitted
# argument from an explicit JSON null.
_OMITTED: Any = object()


def _scope(global_: Any) -> str:
    """Map the tool ``global_`` flag to the connector scope vocabulary.

    A non-bool flag is a typed error, never a truthy coercion into the
    cross-session store.
    """
    if not isinstance(global_, bool):
        raise PrimeError(
            "bad_type",
            f"harness global_ must be bool, got {type(global_).__name__}",
        )
    return "global" if global_ else "local"


def register_harness_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
) -> list[str]:
    """Register the harness family. ``enabled=False`` registers nothing."""
    if not enabled:
        return []

    def connector() -> HarnessConnector:
        return HarnessConnector(root)

    # Every handler decodes through the typed/versioned request boundary
    # before touching state (CONN-01). Decoding precedes capability
    # effects; registry policy/approval already ran, and the registry turns a
    # ``PrimeError`` into the structured error envelope. ``global_`` is the
    # only scope input at the tool surface: ``**extra`` is rejected whole and
    # never merged into the decoded payload, so no undeclared key can reach
    # the cross-session store. Result envelopes are unchanged: bare entry /
    # bare list / {"deleted","id"} / refine result.

    def harness_upsert(
        kind: Any = None,
        id: Any = None,
        title: Any = None,
        body: Any = None,
        tags: Any = None,
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="harness_upsert")
        request = UpsertRequest.from_dict(
            {
                "kind": kind,
                "id": id,
                "title": title,
                "body": body,
                "scope": _scope(global_),
                "tags": [] if tags is None else tags,
                "schema_version": schema_version,
            }
        )
        return connector().upsert(request)["entry"]

    def harness_get(
        kind: Any = None,
        id: Any = None,
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="harness_get")
        request = GetRequest.from_dict(
            {
                "kind": kind,
                "id": id,
                "scope": _scope(global_),
                "schema_version": schema_version,
            }
        )
        entry = connector().get(request)["entry"]
        if entry is not None:
            return entry
        return {"error": f"no {request.kind} entry {request.id!r}"}

    def harness_list(
        kind: Any = None,
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> list:
        reject_extra(extra, what="harness_list")
        request = ListRequest.from_dict(
            {
                "kind": kind,
                "scope": _scope(global_),
                "schema_version": schema_version,
            }
        )
        return connector().list_entries(request)["entries"]

    def harness_delete(
        kind: Any = None,
        id: Any = None,
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="harness_delete")
        request = DeleteRequest.from_dict(
            {
                "kind": kind,
                "id": id,
                "scope": _scope(global_),
                "schema_version": schema_version,
            }
        )
        return {"deleted": connector().delete(request)["deleted"], "id": request.id}

    def harness_refine(
        trigger: Any = None,
        proposals: Any = None,
        trajectory: Any = _OMITTED,
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="harness_refine")
        payload: dict[str, Any] = {
            "trigger": trigger,
            "proposals": proposals,
            "scope": _scope(global_),
            "schema_version": schema_version,
        }
        # ``trajectory`` is any JSON value, null included, so ``None`` cannot
        # mean "omitted"; the decoder owns the missing-field error.
        if trajectory is not _OMITTED:
            payload["trajectory"] = trajectory
        request = RefineRequest.from_dict(payload)
        return connector().refine(request)

    def harness_rollback(
        global_: Any = False,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="harness_rollback")
        request = RollbackRequest.from_dict(
            {"scope": _scope(global_), "schema_version": schema_version}
        )
        return connector().rollback(request)

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
