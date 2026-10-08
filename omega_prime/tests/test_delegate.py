"""Isolated delegate children and the due-job tick."""

from __future__ import annotations

import json
from pathlib import Path

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.delegate import delegate_task, join_delegate
from omega_prime.agent.model import ScriptedModel
from omega_prime.cron.scheduler import JobStore, run_due_jobs
from omega_prime.tools.delegate import register_delegate_tools
from omega_prime.tools.registry import ToolRegistry

CHILD_TOOL = "child_only_tool"
CHILD_MARKER = "child-tool-marker"
CHILD_FINAL = "child-final-response"


def _tool_call(
    name: str, arguments: dict | None = None, call_id: str = "call-1"
) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments or {})},
            }
        ],
    }


def _load(raw: str) -> dict:
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    return parsed


def _user_texts(seen: list) -> list:
    return [
        message.get("content")
        for message in seen
        if isinstance(message, dict) and message.get("role") == "user"
    ]


def test_parent_tool_row_is_the_child_final_response_only():
    calls: list[str] = []

    def child_only_tool():
        calls.append(CHILD_TOOL)
        return CHILD_MARKER

    child_model = ScriptedModel(
        [
            _tool_call(CHILD_TOOL),
            {"role": "assistant", "content": CHILD_FINAL},
        ]
    )
    parent_model = ScriptedModel(
        [
            _tool_call("delegate_task", {"goal": "find the marker"}),
            {"role": "assistant", "content": "parent-done"},
        ]
    )
    parent = Agent(model=parent_model, tools={}, max_iterations=4)
    parent.child_model = child_model
    registry = ToolRegistry()
    register_delegate_tools(registry, parent)
    handler = registry._tools["delegate_task"].handler
    parent.tools = {"delegate_task": handler, CHILD_TOOL: child_only_tool}

    result = run_conversation(parent, "please delegate", system_message="sys")

    tool_row = next(
        message for message in result["messages"] if message.get("role") == "tool"
    )
    assert tool_row["name"] == "delegate_task"
    assert _load(tool_row["content"])["summary"] == CHILD_FINAL
    blob = json.dumps(result["messages"])
    assert CHILD_MARKER not in blob
    assert CHILD_TOOL not in blob
    assert calls == [CHILD_TOOL]
    assert parent_model.call_count == 2
    assert child_model.call_count == 2
    assert CHILD_MARKER in json.dumps(child_model.seen)
    assert CHILD_TOOL in json.dumps(child_model.seen)
    assert CHILD_MARKER not in json.dumps(parent_model.seen)
    assert CHILD_TOOL not in json.dumps(parent_model.seen)
    assert _user_texts(child_model.seen[0]) == ["find the marker"]


def test_child_tool_map_is_a_shallow_copy():
    calls: list[str] = []

    def keep():
        return "kept"

    def drop_me():
        calls.append("drop")
        return "gone"

    tools = {"keep": keep, "drop_me": drop_me}
    parent_model = ScriptedModel([])
    child_model = ScriptedModel(
        [
            _tool_call("drop_me"),
            {"role": "assistant", "content": "after-pop"},
        ]
    )
    parent = Agent(model=parent_model, tools=tools)
    parent_tools = parent.tools
    assert parent_tools is not None
    parent.child_model = child_model
    before_id = id(parent_tools)
    before = dict(parent_tools)
    captured: dict[str, dict] = {}

    def hook(child_tools):
        assert child_tools is not parent_tools
        captured["tools"] = child_tools
        child_tools.pop("drop_me")

    parent.child_tool_hook = hook
    parsed = _load(delegate_task(parent, "go"))

    assert parsed["summary"] == "after-pop"
    assert calls == []
    assert "drop_me" not in captured["tools"]
    assert id(parent_tools) == before_id
    assert dict(parent_tools) == before
    assert parent_tools["keep"] is keep
    assert parent_tools["drop_me"] is drop_me
    assert parent_model.call_count == 0


def test_depth_and_batch_limits_run_no_child():
    child_model = ScriptedModel([{"role": "assistant", "content": "leaf-ok"}])
    parent_model = ScriptedModel([{"role": "assistant", "content": "parent-unused"}])

    def delegate_on_parent():
        return "parent-callable"

    parent_tools = {"delegate_task": delegate_on_parent, "other": lambda: "x"}
    parent = Agent(model=parent_model, tools=parent_tools)
    parent.child_model = child_model
    seen: dict[str, set] = {}

    def hook(child_tools):
        seen["keys"] = set(child_tools)

    parent.child_tool_hook = hook
    parsed = _load(delegate_task(parent, "one", max_depth=1))
    assert parsed["summary"] == "leaf-ok"
    assert "delegate_task" not in seen["keys"]
    assert "other" in seen["keys"]
    assert child_model.call_count == 1
    assert parent_model.call_count == 0
    assert parent.tools is parent_tools
    assert parent.tools["delegate_task"] is delegate_on_parent

    blocked = ScriptedModel([{"role": "assistant", "content": "should-not-run"}])
    deep = Agent(model=parent_model, tools={})
    deep.delegate_depth = 1
    deep.child_model = blocked

    def boom(_tools):
        raise AssertionError("child was built")

    deep.child_tool_hook = boom
    refused = _load(delegate_task(deep, "again", max_depth=1))
    assert "error" in refused
    assert blocked.call_count == 0
    assert parent_model.call_count == 0

    batch_model = ScriptedModel([{"role": "assistant", "content": "should-not-run"}])
    batch_parent = Agent(model=parent_model, tools={})
    batch_parent.child_model = batch_model
    batch_parent.child_tool_hook = boom
    too_many = _load(
        delegate_task(
            batch_parent,
            "ignored",
            tasks=[{"goal": "a"}, {"goal": "b"}],
            max_children=1,
        )
    )
    assert "error" in too_many
    assert batch_model.call_count == 0

    registry = ToolRegistry()
    limited = Agent(model=parent_model, tools={})
    limited.max_children = 1
    limited.child_model = batch_model
    limited.child_tool_hook = boom
    register_delegate_tools(registry, limited)
    dispatched = _load(
        registry.dispatch("delegate_task", {"tasks": [{"goal": "a"}, {"goal": "b"}]})
    )
    assert "error" in dispatched
    assert batch_model.call_count == 0

    room = ScriptedModel(
        [
            {"role": "assistant", "content": "first-child"},
            {"role": "assistant", "content": "second-child"},
        ]
    )
    wide = Agent(model=parent_model, tools={})
    wide.delegate_depth = 2
    wide.max_depth = 3
    wide.max_children = 2
    wide.child_model = room
    wide_registry = ToolRegistry()
    register_delegate_tools(wide_registry, wide)
    both = _load(
        wide_registry.dispatch(
            "delegate_task", {"tasks": [{"goal": "a"}, {"goal": "b"}]}
        )
    )
    assert both["summaries"] == ["first-child", "second-child"]
    assert room.call_count == 2
    assert _user_texts(room.seen[0]) == ["a"]
    assert _user_texts(room.seen[1]) == ["b"]
    assert parent_model.call_count == 0


def test_background_join_runs_the_child_once():
    child_model = ScriptedModel([{"role": "assistant", "content": "bg-summary"}])
    parent_model = ScriptedModel([{"role": "assistant", "content": "parent-unused"}])
    parent = Agent(model=parent_model, tools={})
    parent.child_model = child_model
    hooks: list[str] = []
    parent.child_tool_hook = lambda _tools: hooks.append("hook")
    registry = ToolRegistry()
    register_delegate_tools(registry, parent)

    raw = registry.dispatch("delegate_task", {"goal": "later", "background": True})
    pending = _load(raw)
    assert pending["pending"] is True
    assert isinstance(pending["handle"], str) and pending["handle"]
    assert "summary" not in pending
    assert "bg-summary" not in raw
    assert hooks == []
    assert child_model.call_count == 0
    assert parent_model.call_count == 0

    summary = join_delegate(pending["handle"])
    assert summary == "bg-summary"
    assert hooks == ["hook"]
    assert child_model.call_count == 1

    again = join_delegate(pending["handle"])
    assert again == summary
    assert hooks == ["hook"]
    assert child_model.call_count == 1
    assert parent_model.call_count == 0


def test_due_job_tick_runs_through_the_conversation(tmp_path: Path):
    path = tmp_path / "jobs.json"
    store = JobStore(path)
    now = 1_700_000_000
    tools = {"unused": lambda: "no"}
    model = ScriptedModel(
        [
            {"role": "assistant", "content": "oneshot-text"},
            {"role": "assistant", "content": "interval-first"},
            {"role": "assistant", "content": "interval-second"},
        ]
    )
    oneshot_id = store.schedule("oneshot prompt", now)
    later_id = store.schedule("later prompt", now + 100)
    interval_id = store.schedule("interval prompt", now, interval_seconds=30)
    later_before = json.loads(
        json.dumps(next(job for job in store.jobs if job["id"] == later_id))
    )

    ran = run_due_jobs(store, now, model, tools)

    assert [job["id"] for job in ran] == [oneshot_id, interval_id]
    oneshot = next(job for job in store.jobs if job["id"] == oneshot_id)
    later = next(job for job in store.jobs if job["id"] == later_id)
    interval = next(job for job in store.jobs if job["id"] == interval_id)
    assert oneshot["last_result"] == "oneshot-text"
    assert oneshot["last_ran_at"] == now
    assert oneshot["completed"] is True
    assert oneshot["due_at"] == now
    assert later == later_before
    assert interval["last_result"] == "interval-first"
    assert interval["last_ran_at"] == now
    assert interval["completed"] is False
    assert interval["due_at"] == now + 30
    assert model.call_count == 2
    assert model.tools_seen[0] is tools
    assert model.tools_seen[1] is tools
    assert _user_texts(model.seen[0]) == ["oneshot prompt"]
    assert _user_texts(model.seen[1]) == ["interval prompt"]
    assert "later prompt" not in json.dumps(model.seen)

    run_due_jobs(store, now + 29, model, tools)
    assert model.call_count == 2
    assert oneshot["last_result"] == "oneshot-text"
    assert oneshot["last_ran_at"] == now
    assert interval["due_at"] == now + 30
    assert interval["last_result"] == "interval-first"

    run_due_jobs(store, now + 30, model, tools)
    assert model.call_count == 3
    assert interval["last_result"] == "interval-second"
    assert interval["last_ran_at"] == now + 30
    assert interval["due_at"] == now + 60
    assert oneshot["last_result"] == "oneshot-text"
    assert later == later_before
    assert _user_texts(model.seen[2]) == ["interval prompt"]

    reloaded = JobStore(path)
    assert reloaded.jobs == store.jobs
