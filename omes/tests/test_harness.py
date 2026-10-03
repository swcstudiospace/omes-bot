"""Phase 7: the Omp harness merged into the conversation loop."""

from __future__ import annotations

import threading
import time

from omes.agent.budget import OutputBudget
from omes.agent.compression import USELESS_NOTICE, compress_messages, prune_useless_results
from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.harness import (
    PauseGate,
    commit_speculative,
    inject_steer,
    prepare_speculative,
)
from omes.agent.interrupt import InterruptFlag
from omes.agent.model import ScriptedModel


def _tool_call(name: str, arguments: str = "{}", call_id: str = "call-1") -> dict:
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


def test_turn_emits_start_message_and_end_events():
    tools = {"echo": lambda: "pong"}
    model = ScriptedModel([_tool_call("echo"), {"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools=tools, max_iterations=4)
    result = run_conversation(agent, "ping", system_message="sys")

    assert agent.tools is tools
    kinds = [event["type"] for event in agent.events]
    assert kinds[0] == "turn_start"
    assert kinds[-1] == "turn_end"
    assert kinds.count("message") == len(result["messages"])
    roles = [event["role"] for event in agent.events if event["type"] == "message"]
    assert roles == [row["role"] for row in result["messages"]]
    assert agent.events[-1]["turn_exit_reason"] == result["turn_exit_reason"]


def test_before_model_hook_can_change_or_stop_the_request():
    def hook(messages, tools):
        messages.append({"role": "user", "content": "hook-note"})

    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={}, max_iterations=4, before_model=hook)
    result = run_conversation(agent, "ping")

    assert result["final_response"] == "done"
    assert model.seen[0][-1] == {"role": "user", "content": "hook-note"}

    budget_model = ScriptedModel([{"role": "assistant", "content": "never"}])
    stopper = Agent(
        model=budget_model,
        tools={},
        max_iterations=4,
        before_model=lambda messages, tools: {"stop": True, "reason": "halt"},
    )
    stopped = run_conversation(stopper, "ping")

    assert budget_model.call_count == 0
    assert stopper.budget.remaining == 4
    assert stopped["turn_exit_reason"] == "halt"


def test_before_model_stop_defaults_its_reason():
    model = ScriptedModel([{"role": "assistant", "content": "never"}])
    agent = Agent(
        model=model,
        tools={},
        max_iterations=4,
        before_model=lambda messages, tools: {"stop": True},
    )
    result = run_conversation(agent, "ping")

    assert model.call_count == 0
    assert result["turn_exit_reason"] == "stopped_before_model"


def test_pause_holds_the_loop_and_resume_finishes_it():
    gate = PauseGate()
    gate.pause()
    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={}, max_iterations=4, pause_gate=gate)
    outcome = {}

    def _run():
        outcome["result"] = run_conversation(agent, "ping")

    worker = threading.Thread(target=_run)
    worker.start()
    try:
        time.sleep(0.3)
        assert model.call_count == 0
        assert worker.is_alive()
        gate.resume()
        worker.join(timeout=5)
        assert not worker.is_alive()
    finally:
        gate.resume()
        worker.join(timeout=5)
    assert outcome["result"]["final_response"] == "done"


def test_pause_during_tool_work_does_not_abort_it():
    gate = PauseGate()
    started = threading.Event()

    def slow():
        started.set()
        time.sleep(0.4)
        return "slow-body"

    model = ScriptedModel([_tool_call("slow"), {"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={"slow": slow}, max_iterations=4, pause_gate=gate)
    outcome = {}
    worker = threading.Thread(
        target=lambda: outcome.update(result=run_conversation(agent, "ping"))
    )
    worker.start()
    try:
        assert started.wait(timeout=5)
        gate.pause()
        time.sleep(0.2)
        gate.resume()
        worker.join(timeout=5)
        assert not worker.is_alive()
    finally:
        gate.resume()
        worker.join(timeout=5)
    bodies = [
        row["content"] for row in outcome["result"]["messages"] if row.get("role") == "tool"
    ]
    assert bodies == ["slow-body"]


def test_interrupt_unwinds_a_parked_wait_and_keeps_the_gate():
    gate = PauseGate()
    gate.pause()
    interrupt = InterruptFlag()
    model = ScriptedModel([{"role": "assistant", "content": "never"}])
    agent = Agent(
        model=model, tools={}, max_iterations=4, pause_gate=gate, interrupt=interrupt
    )
    outcome = {}
    worker = threading.Thread(
        target=lambda: outcome.update(result=run_conversation(agent, "ping"))
    )
    worker.start()
    try:
        time.sleep(0.3)
        interrupt.set("stop now")
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert outcome["result"]["interrupted"] is True
        assert model.call_count == 0
        assert gate.paused is True
    finally:
        gate.resume()
        worker.join(timeout=5)


def test_mid_turn_steer_is_its_own_user_row():
    steer = "actually check the log"
    agent = None

    def echo():
        inject_steer(agent, steer)
        return "tool-body"

    model = ScriptedModel([_tool_call("echo"), {"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={"echo": echo}, max_iterations=4)
    result = run_conversation(agent, "ping")

    rows = result["messages"]
    tool_at = next(i for i, row in enumerate(rows) if row.get("role") == "tool")
    assert rows[tool_at]["content"] == "tool-body"
    assert steer not in rows[tool_at]["content"]
    following = rows[tool_at + 1]
    assert following["role"] == "user"
    assert steer in following["content"]
    assert following is not rows[tool_at]


def test_legacy_pending_steer_still_delivers_after_a_tool_result():
    model = ScriptedModel([_tool_call("echo"), {"role": "assistant", "content": "done"}])
    agent = Agent(
        model=model, tools={"echo": lambda: "body"}, max_iterations=4,
        pending_steer="legacy steer",
    )
    result = run_conversation(agent, "ping")

    rows = result["messages"]
    tool_at = next(i for i, row in enumerate(rows) if row.get("role") == "tool")
    following = rows[tool_at + 1]
    assert following["role"] == "user"
    assert "legacy steer" in following["content"]


def test_useless_results_are_not_errors_and_errors_are_never_useless():
    def empty_search():
        return {"content": "zero matches", "useless": True}

    def broken():
        return {"content": "boom", "useless": True, "is_error": True}

    model = ScriptedModel(
        [
            _tool_call("empty_search", call_id="call-1"),
            _tool_call("broken", call_id="call-2"),
            {"role": "assistant", "content": "done"},
        ]
    )
    agent = Agent(
        model=model, tools={"empty_search": empty_search, "broken": broken},
        max_iterations=6,
    )
    result = run_conversation(agent, "ping")

    rows = [row for row in result["messages"] if row.get("role") == "tool"]
    assert [row["content"] for row in rows] == ["zero matches", "boom"]
    assert rows[0]["useless"] is True
    assert rows[0]["is_error"] is not True
    assert rows[1]["is_error"] is True
    assert "useless" not in rows[1]


def test_compression_elides_useless_results_but_never_errors():
    messages: list = [
        {"role": "user", "content": "go"},
        {"role": "tool", "name": "s", "content": "zero matches", "useless": True},
        {"role": "tool", "name": "b", "content": "boom", "is_error": True},
    ]
    assert prune_useless_results(messages) == 1
    assert messages[1]["content"] == USELESS_NOTICE
    assert messages[2]["content"] == "boom"

    short: list = [
        {"role": "user", "content": "go"},
        {"role": "tool", "name": "s", "content": "zero matches", "useless": True},
    ]
    compress_messages(short)
    assert short[1]["content"] == USELESS_NOTICE


def test_output_budget_stops_a_runaway_turn():
    script = [_tool_call("noisy", call_id=f"call-{n}") for n in range(5)]
    model = ScriptedModel(script)
    agent = Agent(
        model=model,
        tools={"noisy": lambda: "x" * 100},
        max_iterations=8,
        output_budget=OutputBudget(10),
    )
    result = run_conversation(agent, "ping")

    assert result["turn_exit_reason"] == "output_budget_exceeded"
    assert model.call_count == 1


def test_speculation_commits_on_match_and_discards_on_mismatch():
    calls = []

    def double(x):
        calls.append(x)
        return f"{x * 2}"

    model = ScriptedModel([_tool_call("double", '{"x": 2}'), {"role": "assistant", "content": "ok"}])
    agent = Agent(
        model=model, tools={"double": double}, max_iterations=4,
        speculative_tools={"double"},
    )
    result = run_conversation(agent, "ping")

    tool_row = next(row for row in result["messages"] if row.get("role") == "tool")
    assert tool_row["content"] == "4"
    assert calls == [2]

    assert commit_speculative(agent, "double", {"x": 3}) is None

    cache_agent = Agent(
        model=model, tools={"double": double}, speculative_tools={"double"}
    )
    prepare_speculative(
        cache_agent, {"double": double}, _tool_call("double", '{"x": 5}')["tool_calls"]
    )
    assert commit_speculative(cache_agent, "double", {"x": 6}) is None
    content, is_error, useless = commit_speculative(cache_agent, "double", {"x": 5})
    assert (content, is_error, useless) == ("10", False, False)
    assert commit_speculative(cache_agent, "double", {"x": 5}) is None


def test_undelivered_queued_steer_is_reported_on_the_result():
    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={}, max_iterations=4)
    inject_steer(agent, "late steer")
    result = run_conversation(agent, "ping")

    assert result["pending_steer"] == "late steer"
    assert getattr(agent, "_steer_queue", []) == []
    assert agent.pending_steer is None
