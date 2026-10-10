"""Learning-surface tools: autolearn capture and advisor rendering."""

from __future__ import annotations

import json
from typing import Any

from omega_prime.skills_runtime.manager import skill_view
from omega_prime.tools.learning_surface import (
    LEARNING_TOOL_NAMES,
    register_learning_surface_tools,
)
from omega_prime.tools.registry import ToolRegistry


class _Approvals:
    def is_approved(self, name):
        return True


def _registry(root, **kwargs) -> ToolRegistry:
    registry = ToolRegistry(approval_log=_Approvals())
    register_learning_surface_tools(registry, root, **kwargs)
    return registry


def _dispatch(registry: ToolRegistry, name: str, arguments: dict) -> dict:
    return json.loads(registry.dispatch(name, arguments))


# --- registration ----------------------------------------------------------------


def test_registers_every_learning_surface_tool(tmp_path):
    registry = _registry(tmp_path)
    served = [schema["function"]["name"] for schema in registry.schemas()]
    assert served == list(LEARNING_TOOL_NAMES)


def test_disabled_registers_nothing(tmp_path):
    registry = ToolRegistry()
    assert register_learning_surface_tools(registry, tmp_path, enabled=False) == []
    assert registry.schemas() == []


def test_write_tools_require_approval(tmp_path):
    registry = ToolRegistry()
    register_learning_surface_tools(registry, tmp_path)
    assert registry.approval_required("autolearn_turn") is True
    for name in ("advisor_note", "advisor_render"):
        assert registry.approval_required(name) is False

    bare = ToolRegistry()
    register_learning_surface_tools(bare, tmp_path)
    out = json.loads(
        bare.dispatch("autolearn_turn", {"tool_calls": 1, "name": "x", "content": "y"})
    )
    assert out == {"error": "approval required", "tool": "autolearn_turn"}


# --- autolearn_turn ---------------------------------------------------------------


def test_autolearn_turn_captures_then_updates_a_skill(tmp_path):
    registry = _registry(tmp_path)
    skills = tmp_path / "skills"

    first = _dispatch(
        registry,
        "autolearn_turn",
        {
            "tool_calls": 3,
            "name": "latin",
            "content": "---\nname: latin\ndescription: Latin lessons\n---\n\nDecline nouns.\n",
        },
    )
    assert first == {"learned": True, "skill": "latin"}
    viewed = json.loads(skill_view("latin", skills_root=skills))
    assert "Decline nouns." in viewed["content"]

    second = _dispatch(
        registry,
        "autolearn_turn",
        {
            "tool_calls": 2,
            "name": "latin",
            "content": "---\nname: latin\ndescription: Latin lessons\n---\n\nDecline verbs.\n",
        },
    )
    assert second == {"learned": True, "skill": "latin"}
    updated = json.loads(skill_view("latin", skills_root=skills))
    assert "Decline verbs." in updated["content"]


def test_autolearn_turn_reports_why_a_turn_was_skipped(tmp_path):
    registry = _registry(tmp_path, min_tool_calls=2)

    insubstantial = _dispatch(
        registry,
        "autolearn_turn",
        {"tool_calls": 1, "name": "latin", "content": "# latin\n"},
    )
    assert insubstantial == {"learned": False, "reason": "fewer than 2 tool calls"}

    blank = _dispatch(
        registry,
        "autolearn_turn",
        {"tool_calls": 3, "name": "latin", "content": "   "},
    )
    assert blank == {"learned": False, "reason": "skill content is blank"}
    assert not (tmp_path / "skills").exists()


def test_autolearn_turn_not_configured_without_a_skills_root():
    registry = _registry(None)
    out = _dispatch(
        registry,
        "autolearn_turn",
        {"tool_calls": 3, "name": "latin", "content": "# latin\n"},
    )
    assert out["error"] == "not_configured"
    assert out["reason"] == "autolearn skills root is not configured"


# --- advisor_note / advisor_render ------------------------------------------------


def test_advisor_note_builds_one_escaped_block(tmp_path):
    registry = _registry(tmp_path)
    out = _dispatch(
        registry,
        "advisor_note",
        {"note": "Fix <this> & that", "severity": "concern"},
    )
    assert out == {
        "note": "Fix <this> & that",
        "severity": "concern",
        "rendered": '<advisory severity="concern">Fix &lt;this&gt; &amp; that</advisory>',
    }

    attributed = _dispatch(
        registry,
        "advisor_note",
        {"note": "Ship it", "severity": "blocker", "advisor": 'qa"x'},
    )
    assert attributed["advisor"] == 'qa"x'
    assert (
        attributed["rendered"]
        == '<advisory severity="blocker" advisor="qa&quot;x">Ship it</advisory>'
    )


def test_advisor_note_answers_error_dicts_for_bad_input(tmp_path):
    registry = _registry(tmp_path)
    bad_severity = _dispatch(
        registry, "advisor_note", {"note": "Tidy", "severity": "yikes"}
    )
    assert bad_severity["error"] == "invalid_advisory"
    assert "severity" in bad_severity["reason"]

    blank_note = _dispatch(registry, "advisor_note", {"note": ""})
    assert blank_note["error"] == "invalid_advisory"


def test_advisor_render_escapes_a_batch(tmp_path):
    registry = _registry(tmp_path)
    out = _dispatch(
        registry,
        "advisor_render",
        {
            "notes": [
                {"note": "Fix <this> & that", "severity": "concern"},
                {"note": "Ship it", "severity": "blocker", "advisor": 'qa"x'},
            ]
        },
    )
    assert out["rendered"].splitlines() == [
        '<advisory severity="concern">Fix &lt;this&gt; &amp; that</advisory>',
        '<advisory severity="blocker" advisor="qa&quot;x">Ship it</advisory>',
    ]


def test_advisor_render_answers_error_dicts_for_bad_input(tmp_path):
    registry = _registry(tmp_path)
    not_a_list = _dispatch(registry, "advisor_render", {"notes": "tidy"})
    assert not_a_list["error"] == "invalid_advisory"

    bad_entry = _dispatch(
        registry, "advisor_render", {"notes": [{"note": "x", "severity": "yikes"}]}
    )
    assert bad_entry["error"] == "invalid_advisory"


# --- unknown arguments ------------------------------------------------------------


def test_unknown_arguments_are_rejected(tmp_path):
    registry = _registry(tmp_path)
    calls: dict[str, dict[str, Any]] = {
        "autolearn_turn": {"tool_calls": 1, "name": "x", "content": "y"},
        "advisor_note": {"note": "Tidy"},
        "advisor_render": {"notes": []},
    }
    for name, arguments in calls.items():
        out = _dispatch(registry, name, {**arguments, "sender": "session"})
        assert out["code"] == "unknown_field"
        assert "sender" in out["reason"]
