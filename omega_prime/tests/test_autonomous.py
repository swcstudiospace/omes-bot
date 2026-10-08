"""Tests for the autonomous driver (Phase 57). Hermetic: gate uses argv."""

from __future__ import annotations

import pytest

from omega_prime.agent.autonomous import (
    STOP_GATE_FAILED,
    STOP_GATE_PASSED,
    STOP_MAX_TOKENS,
    STOP_MAX_TURNS,
    AutonomousBudget,
    AutonomousDriver,
)


def _completed(usage=None):
    return {
        "completed": True,
        "turn_exit_reason": "text_response",
        "usage": usage or {"total_tokens": 10},
    }


def test_budget_validation():
    with pytest.raises(ValueError):
        AutonomousBudget(max_turns=0)
    with pytest.raises(ValueError):
        AutonomousBudget(max_tokens=-1)
    with pytest.raises(ValueError):
        AutonomousBudget(max_minutes=0)
    AutonomousBudget()  # all unbounded is valid


def test_driver_gate_must_be_argv(tmp_path):
    with pytest.raises(ValueError, match="argv"):
        AutonomousDriver(root=tmp_path, gate="echo hi")  # type: ignore[arg-type]


def test_max_turns_stops_cleanly(tmp_path):
    driver = AutonomousDriver(root=tmp_path, budget=AutonomousBudget(max_turns=2))
    driver.start()
    assert driver.after_turn(_completed())["action"] == "continue"
    verdict = driver.after_turn(_completed())
    assert verdict["action"] == "stop"
    assert verdict["reason"] == STOP_MAX_TURNS
    assert verdict["turns"] == 2


def test_max_tokens_stops_cleanly(tmp_path):
    driver = AutonomousDriver(root=tmp_path, budget=AutonomousBudget(max_tokens=25))
    driver.start()
    driver.after_turn(_completed({"total_tokens": 10}))
    driver.after_turn(_completed({"total_tokens": 10}))
    verdict = driver.after_turn(_completed({"total_tokens": 10}))
    assert verdict["reason"] == STOP_MAX_TOKENS
    assert verdict["tokens"] == 30


def test_gate_pass_stops_with_honest_note(tmp_path):
    driver = AutonomousDriver(root=tmp_path, gate=["/bin/true"], gate_retries=0)
    driver.start()
    verdict = driver.after_turn(_completed())
    assert verdict["reason"] == STOP_GATE_PASSED
    assert "verifies only what the gate checks" in verdict["note"]


def test_gate_failure_retries_then_stops(tmp_path):
    driver = AutonomousDriver(root=tmp_path, gate=["/bin/false"], gate_retries=2)
    driver.start()
    verdict = driver.after_turn(_completed())
    assert verdict["reason"] == STOP_GATE_FAILED
    assert "retry window" in verdict["note"]


def test_incomplete_turn_is_not_gated(tmp_path):
    # A budget/interrupt exit is not gated; the loop's own reason stands.
    driver = AutonomousDriver(root=tmp_path, gate=["/bin/false"])
    driver.start()
    verdict = driver.after_turn(
        {"completed": False, "turn_exit_reason": "budget_exhausted"}
    )
    assert verdict["action"] == "stop"
    assert verdict["reason"] != STOP_GATE_FAILED


def test_status_reports_budget(tmp_path):
    driver = AutonomousDriver(
        root=tmp_path, budget=AutonomousBudget(max_turns=5), gate=["/bin/true"]
    )
    driver.start()
    status = driver.status()
    assert status["running"] is True
    assert status["budget"]["max_turns"] == 5
    assert status["gate"] == ["/bin/true"]


def test_autonomous_tools_roundtrip(tmp_path):
    import json as _json

    from omega_prime.tools.autonomous import (
        AUTONOMOUS_TOOL_NAMES,
        register_autonomous_tools,
    )
    from omega_prime.tools.registry import ToolRegistry

    class _Approvals:
        def is_approved(self, name):
            return True

    registry = ToolRegistry(approval_log=_Approvals())
    names = register_autonomous_tools(registry, tmp_path)
    assert names == list(AUTONOMOUS_TOOL_NAMES)
    out = _json.loads(registry.dispatch("autonomous_start", {"max_turns": 3}))
    assert out["started"] is True
    assert out["budget"]["max_turns"] == 3
    status = _json.loads(registry.dispatch("autonomous_status", {}))
    assert status["running"] is True
    stopped = _json.loads(registry.dispatch("autonomous_stop", {}))
    assert stopped["stopped"] is True


def test_autonomous_tools_disabled(tmp_path):
    from omega_prime.tools.autonomous import register_autonomous_tools
    from omega_prime.tools.registry import ToolRegistry

    registry = ToolRegistry()
    assert register_autonomous_tools(registry, tmp_path, enabled=False) == []
    assert registry.schemas() == []
