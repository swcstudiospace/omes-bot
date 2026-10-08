"""Choose which registered schemas are offered to the model.

Adapted from Hermes ``tools/registry.py`` ``get_definitions``, which returns schemas
only for the requested names. A registered tool absent from the roster is omitted.
"""

from __future__ import annotations

from typing import Any


def offered_schemas(registry: Any, roster_names: Any) -> list[dict]:
    """Schemas whose names are in ``roster_names``, in roster order, once each."""
    by_name: dict[str, dict] = {}
    for schema in registry.schemas():
        name = _name(schema)
        if name and name not in by_name:
            by_name[name] = schema
    offered: list[dict] = []
    seen: set[str] = set()
    for name in roster_names or []:
        if not isinstance(name, str) or name in seen or name not in by_name:
            continue
        seen.add(name)
        offered.append(by_name[name])
    return offered


def _name(schema: dict) -> str:
    function = schema.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    name = schema.get("name")
    return name if isinstance(name, str) else ""


__all__ = ["offered_schemas"]
