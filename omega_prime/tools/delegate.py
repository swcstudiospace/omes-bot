"""Register ``delegate_task`` on one registry, bound to one parent agent.

The handler reads ``goal``, ``tasks``, and ``background`` from the model.
``max_depth`` and ``max_children`` stay on the parent and default to 2 and 1.
``parent=None`` keeps the tool served but honestly unconfigured: every call
returns ``not_configured: provider`` instead of a fabricated child, and the
registry's ``runtime_bindings`` publish ``delegate_parent: None`` so callers
(lead-pass dispatch, RLM) see the same absence.
"""

from __future__ import annotations

import json
from typing import Any

from omega_prime.agent.delegate import delegate_task as run_delegate_task
from omega_prime.tools.registry import ToolRegistry

# Offered after the growth tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
DELEG_TOOL_NAMES = ("delegate_task",)

# runtime_bindings key publishing this family's parent (None when no
# provider env is configured — see omega_prime.mcp_server._desk_child_model).
DELEGATE_PARENT_BINDING = "delegate_parent"


def register_delegate_tools(registry: ToolRegistry, parent: Any) -> list[str]:
    """Register ``delegate_task``. The closure calls ``delegate_task(parent, ...)``."""

    def delegate_task(
        goal: str | None = None,
        tasks: list | None = None,
        background: bool = False,
    ) -> str:
        if parent is None:
            return json.dumps({"error": "not_configured: provider"}, ensure_ascii=False)
        return run_delegate_task(
            parent,
            goal,
            tasks=tasks,
            max_depth=getattr(parent, "max_depth", 2),
            max_children=getattr(parent, "max_children", 1),
            background=bool(background),
        )

    handlers = {"delegate_task": delegate_task}
    if tuple(handlers) != DELEG_TOOL_NAMES:
        raise RuntimeError("delegate tool handlers drifted from DELEG_TOOL_NAMES")
    for name in DELEG_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name])
    registry.runtime_bindings[DELEGATE_PARENT_BINDING] = parent
    return list(DELEG_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "delegate_task": (
        "Delegate one goal, or a batch of goals, to a child agent. "
        "The result is the child's final response. "
        "background returns a handle and the child runs when that handle is joined.",
        _object(
            {
                "goal": _string("One task. Omit when tasks is set."),
                "tasks": {
                    "type": "array",
                    "description": "Batch of tasks. Each object has a goal. A longer batch is an error.",
                    "items": _object({"goal": _string("Task goal.")}, ["goal"]),
                },
                "background": {
                    "type": "boolean",
                    "description": "Return a handle before the child runs.",
                },
            },
            [],
        ),
    ),
}


__all__ = ["DELEGATE_PARENT_BINDING", "DELEG_TOOL_NAMES", "register_delegate_tools"]
