"""Tests for the Prime goals port (Phase 57). Hermetic: tmp_path stores."""

from __future__ import annotations

import pytest

from omega_prime.agent.goals import PrimeGoalStore, goal_token_delta_for_usage


def _store(tmp_path):
    return PrimeGoalStore(tmp_path / "goals")


def test_token_delta_for_usage():
    assert goal_token_delta_for_usage({"total_tokens": 50}) == 50
    assert (
        goal_token_delta_for_usage({"prompt_tokens": 30, "completion_tokens": 20}) == 50
    )
    assert goal_token_delta_for_usage({}) == 0
    assert goal_token_delta_for_usage(None) == 0
    assert goal_token_delta_for_usage({"total_tokens": -5}) == 0


def test_goal_persists_across_reopen(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Ship v10", token_budget=1000)
    store.add_step("Write")
    reopened = _store(tmp_path)
    status = reopened.prime_status()
    assert status["objective"] == "Ship v10"
    assert status["prime_status"] == "active"
    assert status["token_budget"] == 1000


def test_set_objective_validates(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.set_objective("   ")
    with pytest.raises(ValueError, match="token_budget"):
        store.set_objective("x", token_budget=0)


def test_budget_accrual_and_exhaustion(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Bounded", token_budget=100)
    store.add_step("Work")
    store.accrue_turn({"total_tokens": 60})
    assert store.prime_status()["tokens_used"] == 60
    assert not store.budget_exhausted()
    store.accrue_turn({"total_tokens": 50})
    assert store.prime_status()["tokens_used"] == 110
    assert store.budget_exhausted()
    # Budget exhausted ⇒ no continuation prompt.
    assert store.continuation_prompt() is None


def test_continuation_prompt_while_active(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Finish", token_budget=1000)
    store.add_step("Do the thing")
    store.add_step("Done")
    prompt = store.continuation_prompt()
    assert prompt is not None and "Finish" in prompt and "Do the thing" in prompt
    # Completing all steps stops continuation.
    store.complete_step(0)
    store.complete_step(1)
    assert store.continuation_prompt() is None


def test_pause_resume_clear(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Pausable")
    store.add_step("s")
    store.pause()
    assert store.prime_status()["prime_status"] == "paused"
    assert store.continuation_prompt() is None
    store.resume()
    assert store.prime_status()["prime_status"] == "active"
    store.clear()
    assert store.prime_status()["objective"] == ""
    assert store.prime_status()["prime_status"] == "cleared"


def test_stale_active_detection(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Stale", token_budget=1000, stale_after_turns=2)
    store.add_step("s")
    assert not store.is_stale()
    store.accrue_turn({})  # no usage ⇒ turns_since_accrual += 1
    assert not store.is_stale()
    store.accrue_turn({})
    assert store.is_stale()
    assert store.continuation_prompt() is None


def test_completion_report(tmp_path):
    store = _store(tmp_path)
    store.set_objective("Report", token_budget=500)
    store.add_step("a")
    store.add_step("b")
    store.complete_step(0)
    store.accrue_turn({"total_tokens": 120})
    report = store.complete()
    assert report["status"] == "completed"
    assert report["steps_total"] == 2 and report["steps_done"] == 1
    assert report["tokens_used"] == 120
    assert report["completed_at"]


def test_base_schema_unchanged(tmp_path):
    # The base GoalStore document keeps its v1 shape; Prime state is a sidecar.
    import json

    store = _store(tmp_path)
    store.set_objective("Base", token_budget=10)
    store.add_step("x")
    base = json.loads((tmp_path / "goals" / "goals.json").read_text())
    assert set(base) == {"schema", "objective", "steps"}
    assert (tmp_path / "goals" / "prime_goal.json").is_file()


def test_replace_goal_validates_everything_before_writing(tmp_path):
    store = _store(tmp_path)
    store.replace_goal("Keep me", ["one"], token_budget=100)
    base = tmp_path / "goals" / "goals.json"
    sidecar = tmp_path / "goals" / "prime_goal.json"
    before = (base.read_bytes(), sidecar.read_bytes())

    with pytest.raises(ValueError):
        store.replace_goal("   ", ["new"])
    with pytest.raises(ValueError, match="token_budget"):
        store.replace_goal("New", ["new"], token_budget=0)
    with pytest.raises(ValueError):
        store.replace_goal("New", ["fine", "   "])

    assert (base.read_bytes(), sidecar.read_bytes()) == before
    reopened = _store(tmp_path)
    assert reopened.status()["objective"] == "Keep me"
    assert [step["text"] for step in reopened.status()["steps"]] == ["one"]


# --- tool family ---------------------------------------------------------------


def test_goal_tools_roundtrip(tmp_path):
    import json as _json

    from omega_prime.tools.goals import GOAL_TOOL_NAMES, register_goal_tools
    from omega_prime.tools.registry import ToolRegistry

    class _Approvals:
        def is_approved(self, name):
            return True

    registry = ToolRegistry(approval_log=_Approvals())
    names = register_goal_tools(registry, tmp_path)
    assert names == list(GOAL_TOOL_NAMES)
    out = _json.loads(
        registry.dispatch(
            "goal_set", {"objective": "Via tool", "steps": ["one", "two"]}
        )
    )
    assert out["objective"] == "Via tool"
    status = _json.loads(registry.dispatch("goal_status", {}))
    assert status["prime_status"] == "active"
    assert len(status["steps"]) == 2


def test_goal_tools_disabled_register_nothing(tmp_path):
    from omega_prime.tools.goals import register_goal_tools
    from omega_prime.tools.registry import ToolRegistry

    registry = ToolRegistry()
    assert register_goal_tools(registry, tmp_path, enabled=False) == []
    assert registry.schemas() == []


def test_goal_write_tools_require_approval(tmp_path):
    from omega_prime.tools.goals import register_goal_tools
    from omega_prime.tools.registry import ToolRegistry

    registry = ToolRegistry()
    register_goal_tools(registry, tmp_path)
    for name in ("goal_set", "goal_pause", "goal_resume", "goal_clear"):
        assert registry.approval_required(name) is True
    assert registry.approval_required("goal_status") is False
