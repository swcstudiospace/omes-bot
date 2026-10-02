"""Phase 2: the Hermes iteration, through run_conversation and a ScriptedModel."""

from __future__ import annotations

import inspect

import pytest

from omes.agent.budget import IterationBudget
from omes.agent.compression import SUMMARY_KIND, compress_messages
from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.interrupt import InterruptFlag
from omes.agent.model import ScriptedModel
from omes.agent.session_lease import SessionLease


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


def _called_from(name: str) -> bool:
    frame = inspect.currentframe()
    while frame is not None:
        if frame.f_code.co_name == name:
            return True
        frame = frame.f_back
    return False


class FrozenMessage(dict):
    """A transcript row that refuses in-place edits outside compress_messages."""

    def __setitem__(self, key, value):
        if key in self and self[key] != value and not _called_from("compress_messages"):
            raise AssertionError(f"edited message field {key}")
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if not _called_from("compress_messages"):
            raise AssertionError(f"deleted message field {key}")
        super().__delitem__(key)

    def update(self, *args, **kwargs):
        if not _called_from("compress_messages"):
            raise AssertionError("updated a message")
        super().update(*args, **kwargs)

    def pop(self, *args):
        if not _called_from("compress_messages"):
            raise AssertionError("popped a message field")
        return super().pop(*args)

    def clear(self):
        if not _called_from("compress_messages"):
            raise AssertionError("cleared a message")
        super().clear()


class AppendOnlyHistory(list):
    """Fails if any code other than compress_messages rewrites an earlier item."""

    def append(self, item):
        super().append(_freeze(item))

    def extend(self, items):
        super().extend(_freeze(item) for item in items)

    def __setitem__(self, index, value):
        if not _called_from("compress_messages"):
            raise AssertionError(f"rewrote the message list at {index!r}")
        super().__setitem__(index, value)

    def __delitem__(self, index):
        if not _called_from("compress_messages"):
            raise AssertionError(f"deleted a message at {index!r}")
        super().__delitem__(index)

    def insert(self, index, value):
        if index != len(self) and not _called_from("compress_messages"):
            raise AssertionError(f"inserted a message at {index}")
        super().insert(index, _freeze(value))

    def pop(self, index=-1):
        if not _called_from("compress_messages"):
            raise AssertionError("popped a message")
        return super().pop(index)

    def clear(self):
        if not _called_from("compress_messages"):
            raise AssertionError("cleared the message list")
        super().clear()


def _freeze(item):
    if isinstance(item, dict) and not isinstance(item, FrozenMessage):
        return FrozenMessage(item)
    return item


def test_system_prompt_is_byte_stable_after_a_tool_round():
    sentinel = "SYSTEM\nBYTES\u00a0stable"
    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "finished"},
        ]
    )

    def echo():
        return "pong"

    agent = Agent(model=model, tools={"echo": echo}, max_iterations=4)
    result = run_conversation(agent, "ping", system_message=sentinel)

    assert model.call_count == 2
    first = model.seen[0][0]
    second = model.seen[1][0]
    assert first["role"] == "system"
    assert second["role"] == "system"
    assert sentinel in first["content"]
    assert second["content"] == first["content"]
    assert second["content"].encode("utf-8") == first["content"].encode("utf-8")
    assert second["content"] is first["content"]
    assert result["messages"][0]["content"] is first["content"]
    assert len(model.seen[1]) > len(model.seen[0])


def test_pending_steer_is_its_own_user_message():
    steer = "look at the log instead"
    tool_body = "tool-body-unchanged"

    def echo():
        agent.pending_steer = steer
        return tool_body

    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "steered"},
        ]
    )
    agent = Agent(model=model, tools={"echo": echo}, max_iterations=4)
    result = run_conversation(agent, "do the thing", system_message="sys")

    messages = result["messages"]
    tool_at = next(index for index, message in enumerate(messages) if message.get("role") == "tool")
    tool_message = messages[tool_at]
    following = messages[tool_at + 1]
    assert tool_message["content"] == tool_body
    assert steer not in tool_message["content"]
    assert following["role"] == "user"
    assert steer in following["content"]
    assert following is not tool_message


def test_only_compress_messages_may_rewrite_history():
    sentinel = "SYSTEM-BYTES-keep"
    history = AppendOnlyHistory()
    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "done"},
        ]
    )

    def echo():
        return "from-tool"

    agent = Agent(model=model, tools={"echo": echo}, max_iterations=4)
    result = run_conversation(agent, "work", system_message=sentinel, conversation_history=history)

    assert result["messages"] is history
    assert len(history) >= 4
    system_before = history[0]["content"]
    assert sentinel in system_before
    length_before = len(history)

    compressed = compress_messages(history)

    assert compressed is history
    assert history[0]["role"] == "system"
    assert history[0]["content"] is system_before
    assert history[0]["content"].encode("utf-8") == system_before.encode("utf-8")
    assert any(isinstance(message, dict) and message.get("display_kind") == SUMMARY_KIND for message in history)
    assert len(history) < length_before


def test_interrupt_stops_before_a_second_model_call():
    interrupt = InterruptFlag()

    def echo():
        interrupt.set("stop now")
        return "ok"

    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "should not be requested"},
        ]
    )
    agent = Agent(model=model, tools={"echo": echo}, max_iterations=5, interrupt=interrupt)
    result = run_conversation(agent, "go", system_message="sys")

    assert model.call_count == 1
    assert model.remaining == 1
    assert any(message.get("role") == "tool" for message in result["messages"])
    assert result["interrupted"] is True
    assert result["final_response"] is not None


def test_max_iterations_stops_while_model_wants_a_tool():
    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "should not be requested"},
        ]
    )

    def echo():
        return "ran"

    agent = Agent(model=model, tools={"echo": echo}, max_iterations=1)
    result = run_conversation(agent, "once", system_message="sys")

    assert model.call_count == 1
    assert model.remaining == 1
    assert agent.budget is not None
    assert agent.budget.remaining == 0
    assert any(message.get("role") == "tool" for message in result["messages"])
    assert any(
        message.get("role") == "assistant" and message.get("tool_calls")
        for message in result["messages"]
    )


def test_budget_stops_when_remaining_hits_zero():
    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "should not be requested"},
        ]
    )

    def echo():
        return "ran"

    agent = Agent(
        model=model,
        tools={"echo": echo},
        max_iterations=8,
        budget=IterationBudget(1),
    )
    result = run_conversation(agent, "budget", system_message="sys")

    assert model.call_count == 1
    assert model.remaining == 1
    assert agent.budget.remaining == 0
    assert result["api_calls"] == 1


def test_lease_released_after_turn_and_on_failure():
    lease = SessionLease()
    held_during: list[bool] = []
    model = ScriptedModel([{"role": "assistant", "content": "ok"}])
    agent = Agent(model=model, tools={}, max_iterations=3, lease=lease)

    def complete(messages, tools=None):
        held_during.append(lease.held)
        return ScriptedModel.complete(model, messages, tools)

    model.complete = complete  # type: ignore[method-assign]
    result = run_conversation(agent, "hi", system_message="sys")

    assert held_during == [True]
    assert lease.held is False
    assert result["final_response"] == "ok"

    failing_lease = SessionLease()
    held_on_failure: list[bool] = []

    class RaisingModel:
        def complete(self, messages, tools=None):
            del messages, tools
            held_on_failure.append(failing_lease.held)
            raise RuntimeError("model failed")

    failing_agent = Agent(model=RaisingModel(), tools={}, max_iterations=3, lease=failing_lease)
    with pytest.raises(RuntimeError, match="model failed"):
        run_conversation(failing_agent, "hi", system_message="sys")

    assert held_on_failure == [True]
    assert failing_lease.held is False
