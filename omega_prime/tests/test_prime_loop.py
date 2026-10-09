# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Loop boundary regressions: registered goal/autonomous state steering real turns.

Consumer-visible behavior only: model call counts, transcript bytes, persisted
store counters, result fields, exception types, and redacted events. No
wiring-only or source-text assertions. Every model here is scripted except the
autonomous quality gates, which run real argv (``/bin/false``) per existing
precedent.
"""

from __future__ import annotations

import json
import threading

import pytest

from omega_prime.agent.autonomous import AutonomousBudget, AutonomousDriver
from omega_prime.agent.budget import IterationBudget
from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.goals import PrimeGoalStore
from omega_prime.agent.harness import events_of
from omega_prime.agent.interrupt import InterruptFlag
from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.providers.base import ProviderError
from omega_prime.tools.autonomous import register_autonomous_tools
from omega_prime.tools.goals import register_goal_tools
from omega_prime.tools.registry import ToolRegistry


class _Approvals:
    def is_approved(self, name):
        return True


class UsageModel(ScriptedModel):
    """Scripted replies with per-call provider usage (dict or None)."""

    def __init__(self, script, usages=None):
        super().__init__(script)
        self._usages = list(usages or [])
        self.last_usage = None

    def complete(self, messages, tools=None):
        message = super().complete(messages, tools)
        self.last_usage = self._usages.pop(0) if self._usages else None
        return message


class FailingModel(UsageModel):
    """Raise a real ProviderError on one call index (1-based)."""

    def __init__(self, script, usages=None, fail_on_call=1):
        super().__init__(script, usages)
        self._fail_on_call = fail_on_call

    def complete(self, messages, tools=None):
        if self.call_count + 1 == self._fail_on_call:
            self.call_count += 1
            self.last_usage = None
            raise ProviderError("timeout boom")
        return super().complete(messages, tools)


def _tool_call(name, arguments="{}", call_id="call-1"):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    }


def _goals_registry(tmp_path, **kwargs):
    registry = ToolRegistry(approval_log=_Approvals())
    register_goal_tools(registry, tmp_path, **kwargs)
    return registry


def _set_goal(registry, objective="Ship it", token_budget=1000, steps=("one", "two")):
    out = json.loads(
        registry.dispatch(
            "goal_set",
            {
                "objective": objective,
                "token_budget": token_budget,
                "steps": list(steps),
            },
        )
    )
    assert out["prime_status"] == "active"
    return out


def _degraded(agent):
    return [e for e in events_of(agent) if e.get("type") == "prime_degraded"]


# --- tracer: goal continuation inside the one turn ---------------------------


def _driver_registry(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_autonomous_tools(registry, tmp_path)
    return registry


def _start_driver(registry, **kwargs):
    out = json.loads(registry.dispatch("autonomous_start", dict(kwargs)))
    assert out["started"] is True
    return out


def test_goal_continuation_runs_inside_one_bounded_turn(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [
            {"role": "assistant", "content": "part one"},
            {"role": "assistant", "content": "part two"},
        ],
        usages=[{"total_tokens": 10}, {"total_tokens": 5}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=2
    )
    transcript_before = agent.messages
    result = agent.run("go")

    # One continuation, then the existing cumulative cap ends the turn.
    assert model.call_count == 2
    assert result["final_response"] == "part two"
    assert result["turn_exit_reason"] == "max_iterations_reached(2/2)"
    # Same transcript list, same lease hold, one journal run: the second call
    # observes the first call's rows plus exactly one continuation user row.
    assert result["messages"] is transcript_before
    assert agent.lease is not None and agent.lease.held is False
    first_seen, second_seen = model.seen
    assert second_seen[-2]["content"] == "part one"
    assert second_seen[-1]["role"] == "user"
    assert "Ship it" in second_seen[-1]["content"]
    assert second_seen[0]["content"] is first_seen[0]["content"]
    # Usage accrued once per logical boundary across both calls.
    assert result["usage"] == {"total_tokens": 15}
    persisted = PrimeGoalStore(tmp_path / "goals").prime_status()
    assert persisted["tokens_used"] == 15


def test_caller_budget_is_never_refilled(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [
            {"role": "assistant", "content": "first"},
            {"role": "assistant", "content": "second"},
        ],
        usages=[{"total_tokens": 3}, {"total_tokens": 4}],
    )
    agent = OmegaPrimeAgent(
        model,
        registry=registry,
        system_message="SYS",
        max_iterations=9,
        budget=IterationBudget(1),
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["turn_exit_reason"] == "budget_exhausted"
    assert result["final_response"] == "first"


def test_outer_cap_bounds_continuation_with_no_second_cap(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [{"role": "assistant", "content": "only"}], usages=[{"total_tokens": 2}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=1
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["turn_exit_reason"] == "max_iterations_reached(1/1)"


# --- usage aggregation -------------------------------------------------------


def test_usage_sums_tool_rounds_and_continuations_without_double_count(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [
            _tool_call("goal_status"),
            {"role": "assistant", "content": "part"},
            {"role": "assistant", "content": "end"},
        ],
        usages=[
            {"prompt_tokens": 4, "completion_tokens": 1, "cache_read_tokens": 2},
            {"prompt_tokens": 6, "completion_tokens": 2, "total_tokens": 8},
            {"total_tokens": 7},
        ],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=3
    )
    result = agent.run("go")
    assert model.call_count == 3
    # Public counters remain the raw key-wise aggregate; budget accounting
    # separately includes the component-only first call (5 + 8 + 7).
    assert result["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 3,
        "cache_read_tokens": 2,
        "total_tokens": 15,
    }
    persisted = PrimeGoalStore(tmp_path / "goals").prime_status()
    assert persisted["tokens_used"] == 20


def test_unknown_usage_stays_unknown(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry, token_budget=1000, steps=("one",))
    model = ScriptedModel([{"role": "assistant", "content": "no counters"}])
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=1
    )
    result = agent.run("go")
    assert result["usage"] is None


def test_successful_usage_survives_a_later_provider_failure(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = FailingModel(
        [_tool_call("goal_status"), {"role": "assistant", "content": "lost"}],
        usages=[{"total_tokens": 9}],
        fail_on_call=2,
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    with pytest.raises(ProviderError):
        agent.run("go")
    assert agent.lease is not None and agent.lease.held is False
    persisted = PrimeGoalStore(tmp_path / "goals").prime_status()
    assert persisted["tokens_used"] == 9


# --- goal lifecycle precedence -----------------------------------------------


def test_paused_goal_stops_continuation(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    json.loads(registry.dispatch("goal_pause", {}))
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["turn_exit_reason"] == "goal_paused"
    assert result["completed"] is False


def test_externally_completed_goal_reports_on_the_result(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    # No goal-complete tool exists: completion arrives through another handle.
    PrimeGoalStore(tmp_path / "goals").complete()
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["turn_exit_reason"] == "goal_completed"
    assert result["completed"] is False
    assert result["goal_completion"]["status"] == "completed"
    assert result["goal_completion"]["objective"] == "Ship it"


def test_exhausted_budget_stops_continuation(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry, token_budget=10)
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 12}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["turn_exit_reason"] == "goal_budget_exhausted"
    assert result["completed"] is False
    persisted = PrimeGoalStore(tmp_path / "goals").prime_status()
    assert persisted["budget_exhausted"] is True


def test_stale_goal_stops_continuation(tmp_path):
    registry = _goals_registry(tmp_path)
    store = PrimeGoalStore(tmp_path / "goals")
    store.set_objective("quiet", stale_after_turns=1)
    store.add_step("only")
    model = ScriptedModel([{"role": "assistant", "content": "held"}])
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["turn_exit_reason"] == "goal_stale"
    assert result["completed"] is False
    assert PrimeGoalStore(tmp_path / "goals").is_stale() is True


def test_cleared_goal_is_no_veto_on_a_running_driver(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("goal_clear", {}))
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 5}))
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
        ],
        usages=[{"total_tokens": 1}, {"total_tokens": 1}, {"total_tokens": 1}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=3
    )
    result = agent.run("go")
    # Cleared before the run with no work observed inside it is absence, not
    # a veto: independent autonomy still spends its budget to the outer cap.
    assert model.call_count == 3
    assert result["turn_exit_reason"] == "max_iterations_reached(3/3)"
    # The cap-terminal boundary still accounts honestly to the stopped driver.
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"


# --- autonomous limits, gates, stickiness ------------------------------------


def test_autonomous_max_turns_stops_honestly_and_stays_stopped(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 2}))
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
        ],
        usages=[{"total_tokens": 4}, {"total_tokens": 4}, {"total_tokens": 4}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=6
    )
    result = agent.run("go")
    assert model.call_count == 2
    assert result["final_response"] == "b"
    assert result["turn_exit_reason"] == "autonomous_stop(autonomous_max_turns)"
    assert result["completed"] is False
    assert result["autonomous_stop"]["reason"] == "autonomous_max_turns"
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 2
    # A stopped driver never restarts: the next turn consults the sticky stop
    # without moving counters.
    again = agent.run("again")
    assert model.call_count == 3
    assert again["autonomous_stop"]["reason"] == "autonomous_max_turns"
    assert holder["driver"].status()["turns"] == 2


def test_autonomous_gate_failure_stops_with_honest_reason(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_autonomous_tools(registry, tmp_path)
    json.loads(
        registry.dispatch(
            "autonomous_start",
            {"max_turns": 5, "gate": ["/bin/false"], "gate_retries": 0},
        )
    )
    model = UsageModel(
        [{"role": "assistant", "content": "a"}, {"role": "assistant", "content": "b"}],
        usages=[{"total_tokens": 2}, {"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "a"
    assert result["turn_exit_reason"] == ("autonomous_stop(autonomous_gate_failed)")
    assert result["completed"] is False
    assert result["autonomous_stop"]["reason"] == "autonomous_gate_failed"


def test_explicit_stop_wins_over_an_active_goal_in_the_same_round(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    model = UsageModel(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "s1",
                        "type": "function",
                        "function": {
                            "name": "autonomous_start",
                            "arguments": '{"max_turns": 5}',
                        },
                    },
                    {
                        "id": "s2",
                        "type": "function",
                        "function": {"name": "autonomous_stop", "arguments": "{}"},
                    },
                ],
            },
            {"role": "assistant", "content": "steady"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[None, {"total_tokens": 3}, {"total_tokens": 3}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # Start and stop landed in one tool round; driver=None alone would look
    # like never-started, but the stop intent wins over the active goal.
    assert model.call_count == 2
    assert result["final_response"] == "steady"
    assert result["turn_exit_reason"] == "autonomous_stop(autonomous_stop)"
    assert result["completed"] is False
    assert result["autonomous_stop"] == {"action": "stop", "reason": "autonomous_stop"}
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"] is None
    # The stopped run stays stopped on the next turn too.
    agent.run("again")
    assert model.call_count == 3


def test_start_without_stop_continues_with_both_prompts(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 5}))
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
            {"role": "assistant", "content": "d"},
        ],
        usages=[{"total_tokens": 1}] * 4,
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    agent.run("go")
    assert model.call_count == 4
    continuation_rows = [row for row in model.seen[-1] if row.get("role") == "user"][
        -2:
    ]
    assert "Ship it" in continuation_rows[0]["content"]


# --- degradation and preserved behavior --------------------------------------


def test_failing_goal_hook_degrades_redacted_without_continuation(tmp_path):
    registry = ToolRegistry()
    secret = "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    def _exploding():
        raise ValueError(f"token {secret} refused")

    registry.runtime_bindings["prime_goals"] = _exploding
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["completed"] is True
    degraded = _degraded(agent)
    assert any(e["family"] == "goals" and "[REDACTED]" in e["error"] for e in degraded)
    assert all(secret not in e["error"] for e in degraded)


def test_failing_driver_hook_degrades_without_continuation(tmp_path):
    registry = ToolRegistry()
    secret = "sk-ant-api03-BBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    class _Broken:
        def after_turn(self, result):
            raise RuntimeError(f"token {secret} leaked")

    registry.runtime_bindings["prime_autonomous"] = {
        "driver": _Broken(),
        "stop_requested": False,
    }
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["completed"] is True
    degraded = _degraded(agent)
    assert len(degraded) == 1
    assert degraded[0]["family"] == "autonomous"
    assert secret not in degraded[0]["error"]


def test_interrupt_is_never_consulted_or_continued(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 5}))
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model,
        registry=registry,
        system_message="SYS",
        max_iterations=4,
        interrupt=InterruptFlag(),
    )
    assert agent.interrupt is not None
    agent.interrupt.set()
    result = agent.run("go")
    assert model.call_count == 0
    assert result["interrupted"] is True
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 0


def test_policy_refusal_survives_hooks_unchanged(tmp_path):
    class _Deny:
        def allows_tool(self, name):
            return name != "blocked_tool"

    registry = ToolRegistry(approval_log=_Approvals(), policy=_Deny())
    registry.register(
        "blocked_tool",
        "Forbidden.",
        {"type": "object", "properties": {}},
        lambda: "never",
    )
    register_goal_tools(registry, tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [_tool_call("blocked_tool"), {"role": "assistant", "content": "routed"}],
        usages=[None, {"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=2
    )
    result = agent.run("go")
    tool_rows = [row for row in result["messages"] if row.get("role") == "tool"]
    assert len(tool_rows) == 1
    assert "policy forbids blocked_tool" in tool_rows[0]["content"]
    assert _degraded(agent) == []


def test_incomplete_finish_accounts_without_gate_or_continuation(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 5}))
    model = UsageModel(
        [{"role": "assistant", "content": "cut", "finish_reason": "length"}],
        usages=[{"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert "length" in result["turn_exit_reason"]
    # Terminal accounting still charges the paid turn to the driver under its
    # incomplete-result semantics: counters move, no gate runs, the run ends
    # honestly, and no continuation is appended.
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"
    assert result["usage"] == {"total_tokens": 2}
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1
    assert holder["driver"].status()["tokens"] == 2


# --- flags-off parity --------------------------------------------------------


def test_flags_off_transcript_roster_and_prompt_unchanged():
    script = [{"role": "assistant", "content": "hello"}]
    plain = Agent(
        model=ScriptedModel([dict(row) for row in script]), tools={}, max_iterations=2
    )
    first = run_conversation(plain, "hi", system_message="SYS")

    registry = ToolRegistry()
    before = {thread.name for thread in threading.enumerate()}
    agent = OmegaPrimeAgent(
        ScriptedModel([dict(row) for row in script]),
        registry=registry,
        system_message="SYS",
        max_iterations=2,
    )
    assert registry.schemas() == []
    second = agent.run("hi")

    assert json.dumps(second["messages"]) == json.dumps(first["messages"])
    assert "usage" not in second
    assert "goal_completion" not in second
    assert "autonomous_stop" not in second
    after = {thread.name for thread in threading.enumerate()}
    new_threads = {
        name
        for name in after - before
        if "sched" in name.lower() or "aps" in name.lower()
    }
    assert new_threads == set()


def test_lease_fast_fail_default_and_wait_opt_in(monkeypatch):
    model = ScriptedModel([{"role": "assistant", "content": "ok"}])
    agent = Agent(model=model, max_iterations=2)
    assert agent.lease is not None
    waiting = threading.Event()
    real_wait = agent.lease._cond.wait

    def observed_wait(*args, **kwargs):
        waiting.set()
        return real_wait(*args, **kwargs)

    monkeypatch.setattr(agent.lease._cond, "wait", observed_wait)
    agent.lease.acquire()
    try:
        with pytest.raises(RuntimeError):
            run_conversation(agent, "hi")
        outcome: dict = {}

        def _waiter():
            outcome["result"] = run_conversation(agent, "hi", wait=True)

        thread = threading.Thread(target=_waiter, daemon=True)
        thread.start()
        assert waiting.wait(timeout=10)
        assert model.call_count == 0
    finally:
        agent.lease.release()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert outcome["result"]["final_response"] == "ok"


# --- terminal accounting: cap, tail, and pre-failure paid work ----------------


def test_outer_cap_terminal_still_accounts_to_goal_and_driver(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = UsageModel(
        [{"role": "assistant", "content": "only"}], usages=[{"total_tokens": 7}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=1
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "only"
    assert result["turn_exit_reason"] == "max_iterations_reached(1/1)"
    assert result["usage"] == {"total_tokens": 7}
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 7
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1
    assert holder["driver"].status()["tokens"] == 7
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"


def test_tool_row_tail_accounts_to_goal_and_driver(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = UsageModel([_tool_call("goal_status")], usages=[{"total_tokens": 6}])
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=1
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 6
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1
    assert holder["driver"].status()["tokens"] == 6
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"


def test_pre_failure_usage_accounts_to_goal_and_driver(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = FailingModel(
        [_tool_call("goal_status"), {"role": "assistant", "content": "lost"}],
        usages=[{"total_tokens": 9}],
        fail_on_call=2,
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    with pytest.raises(ProviderError):
        agent.run("go")
    assert agent.lease is not None and agent.lease.held is False
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 9
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1
    assert holder["driver"].status()["tokens"] == 9


def test_negative_usage_counters_are_ignored(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [
            _tool_call("goal_status"),
            {"role": "assistant", "content": "mid"},
            {"role": "assistant", "content": "end"},
        ],
        usages=[{"total_tokens": 5}, {"total_tokens": -3, "prompt_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=3
    )
    result = agent.run("go")
    assert model.call_count == 3
    # The invalid negative total is dropped; valid known usage is untouched.
    assert result["usage"] == {"total_tokens": 5, "prompt_tokens": 2}
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 7


# --- autonomous token/time limits and real gates -------------------------------


def test_autonomous_max_tokens_stops_honestly(tmp_path):
    registry = _driver_registry(tmp_path)
    _start_driver(registry, max_tokens=5)
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
        ],
        usages=[{"total_tokens": 4}, {"total_tokens": 4}, {"total_tokens": 4}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=6
    )
    result = agent.run("go")
    assert model.call_count == 2
    assert result["turn_exit_reason"] == "autonomous_stop(autonomous_max_tokens)"
    assert result["completed"] is False
    assert result["autonomous_stop"]["reason"] == "autonomous_max_tokens"
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["tokens"] == 8


def test_autonomous_max_minutes_stops_honestly(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import omega_prime.agent.autonomous as autonomous

    now = [0.0]
    monkeypatch.setattr(autonomous, "time", SimpleNamespace(monotonic=lambda: now[0]))
    registry = _driver_registry(tmp_path)
    _start_driver(registry, max_minutes=1)
    model = UsageModel(
        [{"role": "assistant", "content": "a"}], usages=[{"total_tokens": 1}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    now[0] = 61.0
    result = agent.run("go")
    assert model.call_count == 1
    assert result["turn_exit_reason"] == "autonomous_stop(autonomous_max_minutes)"
    assert result["autonomous_stop"]["reason"] == "autonomous_max_minutes"


def test_autonomous_gate_passes_with_honest_reason(tmp_path):
    registry = _driver_registry(tmp_path)
    _start_driver(registry, max_turns=5, gate=["/bin/true"], gate_retries=0)
    model = UsageModel(
        [{"role": "assistant", "content": "a"}, {"role": "assistant", "content": "b"}],
        usages=[{"total_tokens": 2}, {"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["turn_exit_reason"] == "autonomous_stop(autonomous_gate_passed)"
    assert result["completed"] is False
    assert result["autonomous_stop"]["reason"] == "autonomous_gate_passed"
    assert "goal_completion" not in result


def test_component_only_usage_counts_toward_driver_tokens(tmp_path):
    registry = _driver_registry(tmp_path)
    _start_driver(registry, max_tokens=5)
    model = UsageModel(
        [{"role": "assistant", "content": "a"}, {"role": "assistant", "content": "b"}],
        usages=[{"prompt_tokens": 3, "completion_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # Known components with no total still enforce the token budget through
    # the existing token-delta arithmetic, without touching the driver.
    assert model.call_count == 1
    assert result["autonomous_stop"]["reason"] == "autonomous_max_tokens"
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["tokens"] == 5
    # The public aggregate stays faithful to the reported counters.
    assert result["usage"] == {"prompt_tokens": 3, "completion_tokens": 2}


def test_goal_clear_during_turn_cancels_autonomy(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = UsageModel(
        [
            _tool_call("goal_clear"),
            {"role": "assistant", "content": "done"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[None, {"total_tokens": 1}, {"total_tokens": 1}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    # The clear landed mid-run while goal work was ongoing, so the driver's
    # continuation is cancelled for this run even though the driver is live.
    assert model.call_count == 2
    assert result["final_response"] == "done"
    assert result["turn_exit_reason"] == "goal_cleared"
    assert result["completed"] is False
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["prime_status"] == (
        "cleared"
    )


def test_never_set_goal_does_not_veto_independent_autonomy(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_goal_tools(registry, tmp_path)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
        ],
        usages=[{"total_tokens": 1}] * 3,
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=3
    )
    result = agent.run("go")
    # The goals binding is present but no goal was ever set: absence applies
    # no veto, so autonomy spends its budget to the outer cap.
    assert model.call_count == 3
    assert result["final_response"] == "c"
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["prime_status"] == (
        "cleared"
    )


# --- mixed-family degradation --------------------------------------------------


def test_degraded_goal_blocks_autonomy_continuation(tmp_path):
    registry = ToolRegistry()
    secret = "sk-ant-api03-EEEEEEEEEEEEEEEEEEEEEEEEEEEE"

    def _exploding():
        raise ValueError(f"token {secret} refused")

    registry.runtime_bindings["prime_goals"] = _exploding
    driver = AutonomousDriver(root=tmp_path, budget=AutonomousBudget(max_turns=5))
    driver.start()
    registry.runtime_bindings["prime_autonomous"] = {
        "driver": driver,
        "stop_requested": False,
    }
    model = UsageModel(
        [{"role": "assistant", "content": "a"}, {"role": "assistant", "content": "b"}],
        usages=[{"total_tokens": 1}, {"total_tokens": 1}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # The unreadable goal budget stops implicit calls for this run: autonomy
    # cannot spend past it, while the normal response stays available.
    assert model.call_count == 1
    assert result["final_response"] == "a"
    assert result["completed"] is True
    degraded = _degraded(agent)
    assert any(e["family"] == "goals" and "[REDACTED]" in e["error"] for e in degraded)
    assert all(secret not in e["error"] for e in degraded)


def test_degraded_autonomy_blocks_goal_continuation(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    secret = "sk-ant-api03-FFFFFFFFFFFFFFFFFFFFFFFFFFFF"

    class _Broken:
        def after_turn(self, result):
            raise RuntimeError(f"token {secret} leaked")

    registry.runtime_bindings["prime_autonomous"] = {
        "driver": _Broken(),
        "stop_requested": False,
    }
    model = UsageModel(
        [
            {"role": "assistant", "content": "held"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[{"total_tokens": 1}, {"total_tokens": 1}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # A degraded driver cannot permit the goal to extend this same run.
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["completed"] is True
    degraded = _degraded(agent)
    assert len(degraded) == 1
    assert degraded[0]["family"] == "autonomous"
    assert secret not in degraded[0]["error"]


def test_approval_refusal_vetoes_continuation_without_retry(tmp_path):
    class _DenyClear:
        def is_approved(self, name):
            return name != "goal_clear"

    registry = ToolRegistry(approval_log=_DenyClear())
    register_goal_tools(registry, tmp_path)
    _set_goal(registry)
    register_autonomous_tools(registry, tmp_path)
    _start_driver(registry, max_turns=5)
    model = UsageModel(
        [
            _tool_call("goal_clear"),
            {"role": "assistant", "content": "steady"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[None, {"total_tokens": 2}, {"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    tool_rows = [row for row in result["messages"] if row.get("role") == "tool"]
    assert len(tool_rows) == 1
    assert "approval required" in tool_rows[0]["content"]
    # The refusal is honored exactly once: no privileged retry, no Prime
    # continuation past it, no degradation event, normal response available.
    assert model.call_count == 2
    assert result["final_response"] == "steady"
    assert _degraded(agent) == []
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1


# --- heartbeat lifecycle on the real runtime -----------------------------------


def test_heartbeat_lifecycle_with_real_runtime(tmp_path):
    from omega_prime.cron.heartbeat_runtime import HeartbeatRuntime
    from omega_prime.cron.scheduler import JobStore

    clock = [1000.0]
    registry = ToolRegistry()
    runtime = HeartbeatRuntime(tmp_path / "cron" / "jobs.json", clock=lambda: clock[0])
    registry.runtime_bindings["prime_heartbeat"] = runtime
    secret = "sk-ant-api03-DDDDDDDDDDDDDDDDDDDDDDDDDDDD"

    class BeatModel(UsageModel):
        def complete(self, messages, tools=None):
            if self.call_count == 1:
                self.call_count += 1
                raise ProviderError(f"beat failed {secret}")
            return super().complete(messages, tools)

    first = OmegaPrimeAgent(
        BeatModel([{"role": "assistant", "content": "beat done"}]),
        registry=registry,
        system_message="SYS",
        session_name="alpha",
    )
    second = None
    try:
        first.run("foreground")
        prefix = json.loads(json.dumps(first.messages))
        job_id = runtime.schedule(
            "alpha", "beat prompt", interval_seconds=60, due_at=1060
        )
        clock[0] = 1061
        runtime._fire_job(job_id)
        failure = JobStore(runtime.path).jobs[0]["last_result"]
        assert "error" in failure
        assert secret not in failure["error"]
        assert _degraded(first)[0]["family"] == "heartbeat"
        assert secret not in _degraded(first)[0]["error"]
        assert first.messages[: len(prefix)] == prefix

        second = OmegaPrimeAgent(
            ScriptedModel([{"role": "assistant", "content": "replacement beat"}]),
            registry=registry,
            session_name="alpha",
        )
        first.close()
        clock[0] = 1122
        runtime._fire_job(job_id)
        assert JobStore(runtime.path).jobs[0]["last_result"] == "replacement beat"
        assert second.messages[-1]["content"] == "replacement beat"
        assert [row["content"] for row in second.messages if row["role"] == "user"] == [
            "beat prompt"
        ]
        assert first.messages[: len(prefix)] == prefix
        second.close()
        assert runtime.job_ids == []
        second.close()
    finally:
        first.close()
        if second is not None:
            second.close()
        runtime.close()


def test_heartbeat_start_failure_degrades_but_foreground_runs(tmp_path):
    from omega_prime.cron.heartbeat_runtime import HeartbeatRuntime

    class _FailingStart(HeartbeatRuntime):
        def start(self):
            raise RuntimeError("scheduler down")

    registry = ToolRegistry()
    registry.runtime_bindings["prime_heartbeat"] = _FailingStart(
        tmp_path / "cron" / "jobs.json"
    )
    agent = OmegaPrimeAgent(
        ScriptedModel([{"role": "assistant", "content": "hi there"}]),
        registry=registry,
        system_message="SYS",
        max_iterations=2,
    )
    result = agent.run("hi")
    assert result["final_response"] == "hi there"
    degraded = _degraded(agent)
    assert len(degraded) == 1
    assert degraded[0]["family"] == "heartbeat"
    agent.close()
    assert registry.runtime_bindings["prime_heartbeat"].bindings == {}


# --- messaging preservation --------------------------------------------------


def test_two_sessions_share_one_registry_without_interference(tmp_path):
    registry = ToolRegistry()
    calls: list = []

    def _note(text=""):
        calls.append(text)
        return f"noted {text}"

    registry.register("note", "Note text.", {"type": "object", "properties": {}}, _note)
    first = OmegaPrimeAgent(
        ScriptedModel(
            [
                _tool_call("note", '{"text": "a"}'),
                {"role": "assistant", "content": "a done"},
            ]
        ),
        registry=registry,
        system_message="SYS",
        max_iterations=3,
        session_name="a",
    )
    second = OmegaPrimeAgent(
        ScriptedModel(
            [
                _tool_call("note", '{"text": "b"}'),
                {"role": "assistant", "content": "b done"},
            ]
        ),
        registry=registry,
        system_message="SYS",
        max_iterations=3,
        session_name="b",
    )
    first_result = first.run("first turn")
    second_result = second.run("second turn")
    assert calls == ["a", "b"]
    assert first_result["final_response"] == "a done"
    assert second_result["final_response"] == "b done"
    assert first.messages is not second.messages
    assert len(first.messages) == len(second.messages)


# --- reproduced edge-case regressions (Phase 61 gaps) --------------------------


def test_successful_document_text_is_not_a_refusal(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    registry.register(
        "doc_read",
        "Read a document.",
        {"type": "object", "properties": {}},
        lambda: json.dumps(
            {
                "text": "The manual notes approval required or policy forbids "
                "sharing credentials outside the team.",
            }
        ),
    )
    model = UsageModel(
        [
            _tool_call("doc_read"),
            {"role": "assistant", "content": "part one"},
            {"role": "assistant", "content": "part two"},
        ],
        usages=[None, {"total_tokens": 2}, {"total_tokens": 3}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=3
    )
    result = agent.run("go")
    # Successful document data that merely mentions the refusal words is not
    # a failed tool row: the goal continuation still runs to the third call.
    assert model.call_count == 3
    assert result["final_response"] == "part two"
    assert result["turn_exit_reason"] == "max_iterations_reached(3/3)"
    assert _degraded(agent) == []


def test_startup_hook_failure_degrades_vetoes_but_still_accrues(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    factory = registry.runtime_bindings["prime_goals"]
    secret = "sk-ant-api03-GGGGGGGGGGGGGGGGGGGGGGGGGG"
    calls = {"n": 0}

    def _flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(f"key {secret} unreachable")
        return factory()

    registry.runtime_bindings["prime_goals"] = _flaky
    model = UsageModel(
        [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[{"total_tokens": 5}, {"total_tokens": 5}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # The startup read failure degrades loudly (redacted) and vetoes implicit
    # calls for this run, while the normal response stays available and the
    # paid call still accrues once the fresh store is reachable again.
    assert model.call_count == 1
    assert result["final_response"] == "a"
    assert result["completed"] is True
    assert result["usage"] == {"total_tokens": 5}
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 5
    degraded = _degraded(agent)
    assert len(degraded) == 1
    assert degraded[0]["family"] == "goals"
    assert secret not in degraded[0]["error"]


def test_paused_goal_prevents_completion_gate(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    json.loads(registry.dispatch("goal_pause", {}))
    register_autonomous_tools(registry, tmp_path)
    gate_path = tmp_path / "gate.txt"
    _start_driver(registry, max_turns=5, gate=["touch", str(gate_path)], gate_retries=0)
    model = UsageModel(
        [{"role": "assistant", "content": "held"}], usages=[{"total_tokens": 4}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    # The authoritative paused goal stops the turn before any completion
    # gate can run: the gate's side effect must not occur, while paid usage
    # still counts exactly once on both the result and the driver.
    assert model.call_count == 1
    assert result["final_response"] == "held"
    assert result["turn_exit_reason"] == "goal_paused"
    assert result["completed"] is False
    assert not gate_path.exists()
    assert result["usage"] == {"total_tokens": 4}
    holder = registry.runtime_bindings["prime_autonomous"]
    assert holder["driver"].status()["turns"] == 1
    assert holder["driver"].status()["tokens"] == 4
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"
    assert result["autonomous_stop"]["detail"] == "goal_paused"


def test_gate_failure_preserves_producer_diagnostics(tmp_path):
    registry = _driver_registry(tmp_path)
    import sys

    diagnostic = "controlled gate diagnostic"
    gate = [
        sys.executable,
        "-c",
        f"import sys; sys.stderr.write({diagnostic!r}); sys.exit(7)",
    ]
    _start_driver(registry, max_turns=5, gate=gate, gate_retries=0)
    model = UsageModel(
        [{"role": "assistant", "content": "a"}], usages=[{"total_tokens": 2}]
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    stop = result["autonomous_stop"]
    assert stop["reason"] == "autonomous_gate_failed"
    assert stop["stderr"] == diagnostic
    assert stop["turns"] == 1
    assert stop["tokens"] == 2


def test_approval_refusal_reports_honest_unfinished_stop(tmp_path):
    class _DenyClear:
        def is_approved(self, name):
            return name != "goal_clear"

    registry = ToolRegistry(approval_log=_DenyClear())
    register_goal_tools(registry, tmp_path)
    _set_goal(registry)
    model = UsageModel(
        [
            _tool_call("goal_clear"),
            {"role": "assistant", "content": "steady"},
            {"role": "assistant", "content": "must not happen"},
        ],
        usages=[None, {"total_tokens": 2}, {"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=5
    )
    result = agent.run("go")
    tool_rows = [row for row in result["messages"] if row.get("role") == "tool"]
    assert len(tool_rows) == 1
    assert "approval required" in tool_rows[0]["content"]
    # The refusal keeps the normal response but never reads as completed.
    assert model.call_count == 2
    assert result["final_response"] == "steady"
    assert result["turn_exit_reason"] == "approval_refused"
    assert result["completed"] is False
    assert _degraded(agent) == []


def test_incomplete_finish_reports_unfinished(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    register_autonomous_tools(registry, tmp_path)
    json.loads(registry.dispatch("autonomous_start", {"max_turns": 5}))
    model = UsageModel(
        [{"role": "assistant", "content": "cut", "finish_reason": "length"}],
        usages=[{"total_tokens": 2}],
    )
    agent = OmegaPrimeAgent(
        model, registry=registry, system_message="SYS", max_iterations=4
    )
    result = agent.run("go")
    assert model.call_count == 1
    assert result["final_response"] == "cut"
    assert result["turn_exit_reason"] == "incomplete_response(finish_reason=length)"
    assert result["completed"] is False
    assert result["autonomous_stop"]["reason"] == "autonomous_completed"
    assert result["usage"] == {"total_tokens": 2}


@pytest.mark.parametrize("finish_reason", ["end_turn", "stop_sequence"])
def test_anthropic_normal_finishes_continue_goal_work(tmp_path, finish_reason):
    from omega_prime.providers.anthropic import AnthropicProvider

    registry = _goals_registry(tmp_path)
    _set_goal(registry, token_budget=14)
    response = AnthropicProvider().parse_response(
        {
            "content": [{"type": "text", "text": "accepted answer"}],
            "stop_reason": finish_reason,
        }
    )
    model = UsageModel(
        [dict(response), dict(response)], usages=[{"total_tokens": 7}] * 2
    )
    with OmegaPrimeAgent(model, registry=registry, max_iterations=5) as agent:
        result = agent.run("work")
    assert model.call_count == 2
    assert result["final_response"] == "accepted answer"
    assert result["turn_exit_reason"] == "goal_budget_exhausted"
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 14


def test_idle_families_preserve_last_allowed_normal_answer(tmp_path):
    registry = _goals_registry(tmp_path)
    register_autonomous_tools(registry, tmp_path)
    with OmegaPrimeAgent(
        UsageModel([{"role": "assistant", "content": "ordinary answer"}]),
        registry=registry,
        max_iterations=1,
        budget=IterationBudget(1),
    ) as agent:
        result = agent.run("normal turn")
    assert result["completed"] is True
    assert result["final_response"] == "ordinary answer"
    assert result["api_calls"] == 1


def test_interrupt_after_accepted_answer_preserves_it(tmp_path):
    registry = _goals_registry(tmp_path)
    _set_goal(registry)
    interrupt = InterruptFlag()

    class Interrupted(UsageModel):
        def complete(self, messages, tools=None):
            response = super().complete(messages, tools)
            interrupt.set("cancel continuation")
            return response

    model = Interrupted(
        [{"role": "assistant", "content": "accepted before interrupt"}],
        usages=[{"total_tokens": 7}],
    )
    with OmegaPrimeAgent(model, registry=registry, interrupt=interrupt) as agent:
        result = agent.run("work")
    assert result["final_response"] == "accepted before interrupt"
    assert result["completed"] is False
    assert result["interrupted"] is True
    assert model.call_count == 1
    assert PrimeGoalStore(tmp_path / "goals").prime_status()["tokens_used"] == 7


def test_mixed_usage_exhausts_driver_budget_in_one_logical_turn(tmp_path):
    registry = _driver_registry(tmp_path)
    _start_driver(registry, max_tokens=13, max_turns=5)
    model = UsageModel(
        [
            _tool_call("autonomous_status"),
            {"role": "assistant", "content": "paid answer"},
        ],
        usages=[{"prompt_tokens": 4, "completion_tokens": 1}, {"total_tokens": 8}],
    )
    with OmegaPrimeAgent(model, registry=registry, max_iterations=5) as agent:
        result = agent.run("work")
    status = json.loads(registry.dispatch("autonomous_status", {}))
    assert model.call_count == 2
    assert result["autonomous_stop"]["reason"] == "autonomous_max_tokens"
    assert result["usage"]["total_tokens"] == 8
    assert status["tokens"] == 13
    assert status["turns"] == 1
