# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the learning-surface tool family on one registry.

Two planes from ``omega_prime.learning`` get a served boundary here:
``Autolearn`` lesson capture (``learning/autolearn.py``) and the advisor
note renderer (``learning/advisor.py``). The third plane — the goal store
(``learning/goals.py``) — is already served by the goals family
(``tools/goals.py``) through ``PrimeGoalStore`` and is not re-registered.
No tool needs a model or provider env: the learning package is model-free
by port (``learning/__init__.py``). The only configured resource is the
skills root the autolearn writer captures into; with ``root=None`` the
capture tool stays served and answers ``not_configured`` (the delegate
family's honest-absence precedent).

Offered after the goals tools. omega_prime/contracts/tool-rosters/omega-prime.yaml lists this.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.learning.advisor import SEVERITIES, advise, format_advisories
from omega_prime.learning.autolearn import Autolearn
from omega_prime.prime.types import reject_extra
from omega_prime.tools.registry import ToolRegistry

LEARNING_TOOL_NAMES = (
    "autolearn_turn",
    "advisor_note",
    "advisor_render",
)

_WRITE_TOOLS = frozenset({"autolearn_turn"})


def register_learning_surface_tools(
    registry: ToolRegistry,
    root: str | Path | None,
    *,
    enabled: bool = True,
    min_tool_calls: int = 1,
) -> list[str]:
    """Register the learning-surface family. ``enabled=False`` registers nothing."""
    if not enabled:
        return []

    # A fresh ``Autolearn`` per dispatch (the goals-family discipline: never
    # a cached store), so every capture decodes against the live skills
    # root. Handlers reject undeclared arguments before touching state and
    # answer with explicit error dicts, never raised exceptions; the
    # advisor half is a pure renderer with no configured resource.

    def autolearn_turn(
        tool_calls: Any = None,
        name: Any = None,
        content: Any = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="autolearn_turn")
        if root is None:
            return _error("not_configured", "autolearn skills root is not configured")
        learner = Autolearn(Path(root) / "skills", min_tool_calls=min_tool_calls)
        return learner.consider_turn(tool_calls, name, content)

    def advisor_note(
        note: Any = None,
        severity: Any = "nit",
        advisor: Any = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="advisor_note")
        try:
            return advise(note, severity, advisor)
        except ValueError as exc:
            return _error("invalid_advisory", str(exc))

    def advisor_render(notes: Any = None, **extra: Any) -> dict:
        reject_extra(extra, what="advisor_render")
        if not isinstance(notes, list):
            return _error("invalid_advisory", "notes must be a list of objects")
        try:
            return {"rendered": format_advisories(notes)}
        except ValueError as exc:
            return _error("invalid_advisory", str(exc))

    handlers: dict[str, Callable[..., Any]] = {
        "autolearn_turn": autolearn_turn,
        "advisor_note": advisor_note,
        "advisor_render": advisor_render,
    }
    if tuple(handlers) != LEARNING_TOOL_NAMES:
        raise RuntimeError(
            "learning-surface tool handlers drifted from LEARNING_TOOL_NAMES"
        )
    for name in LEARNING_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(LEARNING_TOOL_NAMES)


def _error(code: str, reason: str) -> dict:
    return {"error": code, "reason": reason}


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SEVERITY = {
    "type": "string",
    "enum": list(SEVERITIES),
    "description": "nit, concern, or blocker.",
}

_SCHEMAS: dict[str, tuple[str, dict]] = {
    "autolearn_turn": (
        "Consider one finished turn for lesson capture: with enough tool calls, "
        "write the lesson as a skill (created, or edited when it already exists). "
        "Answers learned false with a reason when the turn was insubstantial.",
        _object(
            {
                "tool_calls": {
                    "type": "integer",
                    "description": "Tool calls the finished turn made.",
                },
                "name": _string("Skill name for the lesson."),
                "content": _string("Lesson content as SKILL.md text."),
            },
            ["tool_calls", "name", "content"],
        ),
    ),
    "advisor_note": (
        "Build one advisor note together with its rendered advisory block.",
        _object(
            {
                "note": _string("The advice text."),
                "severity": _SEVERITY,
                "advisor": _string("Who gave the note. Optional."),
            },
            ["note"],
        ),
    ),
    "advisor_render": (
        "Render several advisor notes as escaped advisory lines.",
        _object(
            {
                "notes": {
                    "type": "array",
                    "description": "Notes to render.",
                    "items": _object(
                        {
                            "note": _string("The advice text."),
                            "severity": _SEVERITY,
                            "advisor": _string("Who gave the note. Optional."),
                        },
                        ["note"],
                    ),
                },
            },
            ["notes"],
        ),
    ),
}


__all__ = ["LEARNING_TOOL_NAMES", "register_learning_surface_tools"]
