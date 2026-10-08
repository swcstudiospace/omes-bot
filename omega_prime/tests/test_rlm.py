"""Tests for the RLM recursion port (Phase 55).

Hermetic: scripted child runners, tmp_path session dirs, no network.
Behavior contract: prime-agent rlm/__init__.py + rlm_host.rs @ 967eb13f.
"""

from __future__ import annotations

import json
import time

import pytest

from omega_prime.agent.rlm import (
    NO_HOST_CREATE_SESSION_ERROR,
    NO_HOST_SPAWN_ERROR,
    RLM_PROGRESS_NOTE_MAX_LENGTH,
    NoRlmHost,
    RlmHost,
    host_for,
)
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.rlm import RLM_TOOL_NAMES, register_rlm_tools


class _Parent:
    """Minimal parent agent stand-in (delegate.py parent-attr precedent)."""

    def __init__(self, tmp_path, depth=0, max_depth=2, max_children=4):
        self.depth = depth
        self.max_depth = max_depth
        self.max_children = max_children
        self.session_dir = str(tmp_path)
        self.session_name: str | None = None


def _scripted_runner(answer="child done", delay=0.0):
    def run(prompt, model=None, thinking=None):
        if delay:
            time.sleep(delay)
        return f"{answer}: {prompt}"

    return run


def _host(tmp_path, runner=None, **kwargs):
    return RlmHost(_Parent(tmp_path, **kwargs), run_child=runner or _scripted_runner())


# --- spawn -------------------------------------------------------------------


def test_spawn_returns_handle_with_prime_fields(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("do the thing", name="researcher")
    assert handle.rlm_child_id.startswith("rlm-")
    assert handle.name == "researcher"
    assert handle.model is None
    assert handle.session_dir.name == handle.rlm_child_id


def test_spawn_requires_prompt_str(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(TypeError, match="prompt must be str"):
        host.spawn(123, name="x")


def test_spawn_rejects_duplicate_sibling_name(tmp_path):
    host = _host(tmp_path)
    host.spawn("a", name="dup")
    with pytest.raises(ValueError, match='named "dup" already exists'):
        host.spawn("b", name="dup")


def test_spawn_enforces_child_limit(tmp_path):
    host = _host(tmp_path, max_children=1)
    host.spawn("a", name="only")
    with pytest.raises(ValueError, match="child limit reached"):
        host.spawn("b", name="second")


def test_spawn_enforces_depth_limit(tmp_path):
    host = _host(tmp_path, depth=2, max_depth=2)
    with pytest.raises(ValueError, match="depth limit reached"):
        host.spawn("a", name="too-deep")


# --- collect -------------------------------------------------------------------


def test_collect_done_child_returns_typed_result(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("task", name="worker")
    results = host.collect([handle], timeout_ms=5000)
    assert len(results) == 1
    result = results[0]
    assert result.rlm_child_id == handle.rlm_child_id
    assert result.status == "done"
    assert result.settled is True
    assert "child done: task" in (result.answer_preview or "")


def test_collect_none_selects_all_living_children(tmp_path):
    host = _host(tmp_path)
    host.spawn("a", name="one")
    host.spawn("b", name="two")
    results = host.collect(timeout_ms=5000)
    assert {r.session_name for r in results} == {"one", "two"}


def test_collect_timeout_returns_snapshots_never_raises(tmp_path):
    host = _host(tmp_path, runner=_scripted_runner(delay=5.0))
    handle = host.spawn("slow", name="slowpoke")
    start = time.monotonic()
    results = host.collect([handle], timeout_ms=100)
    elapsed = time.monotonic() - start
    assert elapsed < 2.0  # returned on elapse, did not wait for the child
    assert results[0].status == "running"
    assert results[0].settled is False
    host.shutdown()


def test_collect_zero_timeout_is_nonblocking_snapshot(tmp_path):
    host = _host(tmp_path, runner=_scripted_runner(delay=5.0))
    host.spawn("slow", name="slowpoke")
    results = host.collect(timeout_ms=0)
    assert results[0].status == "running"
    host.shutdown()


def test_collect_unknown_target_raises_verbatim(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(
        ValueError,
        match='No direct RLM subagent matches "ghost" in the current parent session',
    ):
        host.collect(["ghost"])


def test_collect_rejects_bad_selector_type(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(TypeError, match="collect target must be"):
        host.collect([object()])


def test_collect_child_error_is_retained_as_error_status(tmp_path):
    def boom(prompt, model=None, thinking=None):
        raise RuntimeError("child exploded")

    host = _host(tmp_path, runner=boom)
    handle = host.spawn("x", name="fails")
    results = host.collect([handle], timeout_ms=5000)
    assert results[0].status == "error"
    assert results[0].settled is True
    assert "child exploded" in (results[0].error or "")


def test_collect_rejects_bool_timeout(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(TypeError, match="timeout_ms must be int"):
        host.collect(timeout_ms=True)


# --- list / delete / rename ----------------------------------------------------


def test_list_subagents_status_vocabulary(tmp_path):
    host = _host(tmp_path)
    host.spawn("a", name="one")
    host.collect(timeout_ms=5000)
    host.spawn("b", name="two")
    rows = {r.session_name: r for r in host.list_subagents()}
    assert rows["one"].status == "completed"
    assert rows["two"].status in {"running", "completed"}
    assert rows["one"].status in {"running", "completed", "error"}


def test_delete_reaps_child_and_result(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("a", name="one")
    host.collect([handle], timeout_ms=5000)
    out = host.delete_subagent(handle)
    assert out["deleted"] == handle.rlm_child_id
    assert host.list_subagents() == []
    with pytest.raises(ValueError, match="No direct RLM subagent matches"):
        host.collect([handle])


def test_delete_unknown_target_verbatim_error(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(
        ValueError,
        match='No direct RLM subagent matches "ghost" in the current parent session',
    ):
        host.delete_subagent("ghost")


def test_rename_child_and_self(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("a", name="old")
    out = host.rename(handle, "new")
    assert out["name"] == "new"
    assert host.list_subagents()[0].session_name == "new"
    parent = _Parent(tmp_path)
    host2 = RlmHost(parent, run_child=_scripted_runner())
    assert host2.rename("self", "parent-name")["renamed"] == "self"
    assert parent.session_name == "parent-name"


# --- progress notes --------------------------------------------------------------


def test_progress_note_accept_then_throttle(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("a", name="one")
    first = host.progress_note(handle.rlm_child_id, "working on it")
    assert first.accepted is True
    second = host.progress_note(handle.rlm_child_id, "still going")
    assert second.accepted is False
    assert second.retry_after_ms is not None and second.retry_after_ms > 0


def test_progress_note_length_cap_counts_utf16_code_units(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("a", name="one")
    too_long = "x" * (RLM_PROGRESS_NOTE_MAX_LENGTH + 1)
    with pytest.raises(ValueError, match="512 UTF-16 code units"):
        host.progress_note(handle.rlm_child_id, too_long)


# --- create_session -----------------------------------------------------------------


def test_create_session_persists_file_and_spawns(tmp_path):
    host = _host(tmp_path)
    handle = host.create_session("long task", name="durable", cwd=str(tmp_path))
    assert handle.session_file.is_file()
    assert handle.name == "durable"
    assert handle.session_id == handle.active_session_id
    # The created session runs like a spawned child.
    assert any(r.session_name == "durable" for r in host.list_subagents())


# --- degraded no-host surface -------------------------------------------------------


def test_no_host_spawn_error_verbatim():
    with pytest.raises(RuntimeError, match=NO_HOST_SPAWN_ERROR):
        NoRlmHost().spawn("x", name="y")


def test_no_host_create_session_error_verbatim():
    with pytest.raises(RuntimeError, match=NO_HOST_CREATE_SESSION_ERROR):
        NoRlmHost().create_session("x")


def test_no_host_list_and_empty_collect_are_empty():
    assert NoRlmHost().list_subagents() == []
    assert NoRlmHost().collect() == []


def test_no_host_delete_and_targeted_collect_raise_verbatim():
    with pytest.raises(ValueError, match='No direct RLM subagent matches "ghost"'):
        NoRlmHost().delete_subagent("ghost")
    with pytest.raises(ValueError, match='No direct RLM subagent matches "ghost"'):
        NoRlmHost().collect(["ghost"])


def test_no_host_self_rename_lands_locally():
    assert NoRlmHost().rename("self", "named")["renamed"] == "self"


def test_host_for_gates_on_enabled(tmp_path):
    parent = _Parent(tmp_path)
    assert isinstance(host_for(parent, False), NoRlmHost)
    assert isinstance(host_for(parent, True, run_child=_scripted_runner()), RlmHost)


# --- tool family registration ---------------------------------------------------


def test_register_rlm_tools_registers_all_seven(tmp_path):
    registry = ToolRegistry()
    parent = _Parent(tmp_path)
    names = register_rlm_tools(registry, parent, run_child=_scripted_runner())
    assert names == list(RLM_TOOL_NAMES)
    for name in RLM_TOOL_NAMES:
        assert name in [s["function"]["name"] for s in registry.schemas()]


def test_disabled_family_registers_nothing(tmp_path):
    registry = ToolRegistry()
    parent = _Parent(tmp_path)
    assert register_rlm_tools(registry, parent, enabled=False) == []
    assert registry.schemas() == []


def test_write_tools_require_approval(tmp_path):
    registry = ToolRegistry()
    register_rlm_tools(registry, _Parent(tmp_path), run_child=_scripted_runner())
    for name in (
        "rlm_spawn",
        "rlm_create_session",
        "rlm_delete_subagent",
        "rlm_rename",
    ):
        assert registry.approval_required(name) is True
    for name in ("rlm_collect", "rlm_list_subagents", "rlm_progress_note"):
        assert registry.approval_required(name) is False


def test_dispatch_round_trip_json(tmp_path):
    class _Approvals:
        def is_approved(self, name):
            return True

    registry = ToolRegistry(approval_log=_Approvals())
    register_rlm_tools(registry, _Parent(tmp_path), run_child=_scripted_runner())
    out = json.loads(registry.dispatch("rlm_spawn", {"prompt": "hi", "name": "kid"}))
    assert out["name"] == "kid"
    assert out["rlm_child_id"].startswith("rlm-")
    out = json.loads(
        registry.dispatch(
            "rlm_collect", {"targets": [out["rlm_child_id"]], "timeout_ms": 5000}
        )
    )
    assert out[0]["status"] == "done"
    assert out[0]["settled"] is True


def test_write_tool_dispatch_requires_approval(tmp_path):
    registry = ToolRegistry()  # no approval log ⇒ flagged tools stay unapproved
    register_rlm_tools(registry, _Parent(tmp_path), run_child=_scripted_runner())
    out = json.loads(registry.dispatch("rlm_spawn", {"prompt": "hi", "name": "kid"}))
    assert out == {"error": "approval required", "tool": "rlm_spawn"}
