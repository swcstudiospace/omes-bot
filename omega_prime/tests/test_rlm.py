"""Tests for the RLM recursion port (Phase 55).

Hermetic: scripted child runners, tmp_path session dirs, no network.
Behavior contract: prime-agent rlm/__init__.py + rlm_host.rs @ 967eb13f.
"""

from __future__ import annotations

import json
import threading

import pytest

from omega_prime.agent import rlm as rlm_module
from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.rlm import (
    NO_HOST_CREATE_SESSION_ERROR,
    NO_HOST_SPAWN_ERROR,
    RLM_PROGRESS_NOTE_MAX_LENGTH,
    NoRlmHost,
    RlmHost,
    host_for,
)
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.session.persist import load_session
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.rlm import RLM_TOOL_NAMES, register_rlm_tools


class _Parent:
    """Minimal parent agent stand-in (delegate.py parent-attr precedent)."""

    def __init__(self, tmp_path, delegate_depth=0, max_depth=2, max_children=4):
        self.delegate_depth = delegate_depth
        self.max_depth = max_depth
        self.max_children = max_children
        self.session_dir = str(tmp_path)
        self.session_name: str | None = None
        self.conversation = ""


def _scripted_runner(answer="child done"):
    def run(prompt, model=None, thinking=None):
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
    host = _host(tmp_path, delegate_depth=2, max_depth=2)
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


@pytest.mark.parametrize("timeout_ms", [0, 50])
def test_collect_before_release_is_unsettled_then_recovers(tmp_path, timeout_ms):
    gate = threading.Event()

    def blocked(prompt, model=None, thinking=None):
        if not gate.wait(5):
            raise RuntimeError("child release barrier expired")
        return "released answer"

    host = _host(tmp_path, runner=blocked)
    try:
        handle = host.spawn("slow", name="slowpoke")
        result = host.collect([handle], timeout_ms=timeout_ms)[0]
        assert result.status == "running"
        assert result.settled is False
        gate.set()
        result = host.collect([handle], timeout_ms=5000)[0]
        assert result.status == "done"
        assert result.answer_preview == "released answer"
    finally:
        gate.set()
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
    handle = host.create_session("long task", name="durable")
    # Real recoverable document, not an empty touched file or fake extension.
    assert handle.session_file.suffix == ".json"
    assert handle.session_file.is_file()
    assert handle.session_file.stat().st_size > 0
    assert handle.name == "durable"
    assert handle.session_id == handle.active_session_id
    document = load_session(tmp_path, handle.session_id)
    # The child prompt is the durable input, whenever the worker settles.
    assert document["messages"][0] == {"role": "user", "content": "long task"}
    assert document["metadata"]["rlm_child_id"].startswith("rlm-")
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


# --- durable sessions and collect-only channel (61-04) ---------------------------


class _ScriptedAgent:
    """Explicit scripted child agent: prompt in, answer out, bound progress."""

    def __init__(self, answer="agent done"):
        self.answer = answer
        self.notes = []
        self.prompts = []

    def __call__(self, prompt, *, model=None, thinking=None, progress=None):
        self.prompts.append(prompt)
        if progress is not None:
            self.notes.append(progress("working"))
            self.notes.append(progress("still going"))
        return f"{self.answer}: {prompt}"


def test_spawn_persists_only_child_prompt(tmp_path):
    gate = threading.Event()

    def gated(prompt, model=None, thinking=None):
        gate.wait(10.0)
        return "done"

    parent = _Parent(tmp_path)
    parent.conversation = "PARENT-SECRET-CONTEXT-MARKER"
    host = RlmHost(parent, run_child=gated)
    try:
        host.spawn("child task", name="kid")
        rows = host.list_subagents()
        assert rows[0].session_id
        assert rows[0].active_session_id == rows[0].session_id
        document = load_session(tmp_path, rows[0].session_id)
        assert document["messages"] == [{"role": "user", "content": "child task"}]
        assert "PARENT-SECRET-CONTEXT-MARKER" not in json.dumps(document)
    finally:
        gate.set()
    assert host.collect(timeout_ms=5000)[0].status == "done"


def test_fresh_host_recovers_completed_child(tmp_path):
    host = _host(tmp_path)
    host.spawn("recover me", name="kid")
    assert host.collect(timeout_ms=5000)[0].status == "done"
    session_id = host.list_subagents()[0].session_id
    # Recovery is wired into host creation: the fresh host already lists the
    # settled record without any manual call.
    fresh = _host(tmp_path)
    rows = fresh.list_subagents()
    assert [row.session_id for row in rows] == [session_id]
    assert rows[0].status == "completed"
    results = fresh.collect(timeout_ms=1000)
    assert results[0].status == "done"
    assert "child done: recover me" in (results[0].answer_preview or "")
    with pytest.raises(ValueError, match="already registered"):
        fresh.recover_session(session_id)


def test_fresh_host_recovers_failed_child_as_error_never_done(tmp_path):
    def boom(prompt, model=None, thinking=None):
        raise RuntimeError("child exploded")

    host = _host(tmp_path, runner=boom)
    host.spawn("doomed", name="kid")
    assert host.collect(timeout_ms=5000)[0].status == "error"
    session_id = host.list_subagents()[0].session_id
    fresh = _host(tmp_path)
    rows = fresh.list_subagents()
    assert [row.session_id for row in rows] == [session_id]
    assert rows[0].status == "error"
    results = fresh.collect(timeout_ms=1000)
    assert results[0].status == "error"
    assert results[0].settled is True
    assert "child exploded" in (results[0].error or "")


def test_interrupted_child_recovers_as_explicit_error_without_replay(tmp_path):
    gate = threading.Event()
    calls = []

    def hanging(prompt, model=None, thinking=None):
        calls.append(prompt)
        gate.wait(10.0)
        return "late answer"

    host = _host(tmp_path, runner=hanging)
    try:
        host.spawn("unfinished", name="kid")
        host.shutdown()

        def exploded(prompt, model=None, thinking=None):
            raise AssertionError("interrupted child was replayed")

        # Constructor recovery itself must not invoke any runner.
        fresh = _host(tmp_path, runner=exploded)
        rows = fresh.list_subagents()
        assert len(rows) == 1
        assert rows[0].status == "error"
        results = fresh.collect(timeout_ms=1000)
        assert results[0].status == "error"
        assert results[0].settled is True
        assert "interrupted" in (results[0].error or "")
        assert "not replayed" in (results[0].error or "")
        assert calls == ["unfinished"]
    finally:
        gate.set()


def test_recover_unknown_session_raises_key_error(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(KeyError):
        host.recover_session("no-such-child")


def test_bound_progress_accept_then_throttle_updates_snapshot(tmp_path):
    agent = _ScriptedAgent()
    host = _host(tmp_path, runner=agent)
    host.spawn("task", name="kid")
    assert host.collect(timeout_ms=5000)[0].status == "done"
    assert agent.notes[0].accepted is True
    assert agent.notes[1].accepted is False
    assert agent.notes[1].retry_after_ms is not None
    assert agent.notes[1].retry_after_ms > 0
    assert host.list_subagents()[0].progress_note == "working"


def test_bound_progress_isolated_between_children(tmp_path):
    seen = {}

    def noting(tag):
        def run(prompt, model=None, thinking=None, progress=None):
            if progress is not None:
                seen[tag] = progress(f"note-{tag}")
            return tag

        return run

    class _Router:
        def __call__(self, prompt, model=None, thinking=None, progress=None):
            tag = "alpha" if "alpha" in prompt else "beta"
            return noting(tag)(
                prompt, model=model, thinking=thinking, progress=progress
            )

    host = _host(tmp_path, runner=_Router())
    host.spawn("alpha work", name="alpha")
    host.spawn("beta work", name="beta")
    assert host.collect(timeout_ms=5000)[0].status == "done"
    assert seen["alpha"].accepted is True
    assert seen["beta"].accepted is True
    rows = {row.session_name: row for row in host.list_subagents()}
    assert rows["alpha"].progress_note == "note-alpha"
    assert rows["beta"].progress_note == "note-beta"


def test_progress_note_unknown_child_raises(tmp_path):
    host = _host(tmp_path)
    with pytest.raises(ValueError, match='No direct RLM subagent matches "ghost"'):
        host.progress_note("ghost", "hello")


def test_answer_visible_only_through_collect(tmp_path):
    host = _host(tmp_path, runner=_scripted_runner(answer="top-secret-answer"))
    handle = host.spawn("task", name="kid")
    collected = host.collect([handle], timeout_ms=5000)
    assert collected[0].status == "done"
    assert "top-secret-answer" in (collected[0].answer_preview or "")
    for row in host.list_subagents():
        assert row.answer_preview is None
        assert "top-secret-answer" not in repr(row)
    receipt = host.delete_subagent(handle)
    assert "top-secret-answer" not in json.dumps(receipt)
    with pytest.raises(ValueError, match="No direct RLM subagent"):
        host.collect([handle])


def test_unconfigured_runner_is_explicit_error_not_delivery(tmp_path):
    parent = _Parent(tmp_path)
    host = RlmHost(parent, run_child=None)
    handle = host.spawn("task", name="kid")
    results = host.collect([handle], timeout_ms=2000)
    assert results[0].status == "error"
    assert "no child runner configured" in (results[0].error or "")


def test_recovery_isolated_to_owning_parent(tmp_path):
    owner = _Parent(tmp_path)
    owner.session_name = "alpha"
    host = RlmHost(owner, run_child=_scripted_runner())
    session_id = host.create_session("task", name="kid").session_id
    assert host.collect(timeout_ms=5000)[0].status == "done"
    stranger = _Parent(tmp_path)
    stranger.session_name = "beta"
    fresh = RlmHost(stranger, run_child=_scripted_runner())
    assert fresh.list_subagents() == []
    with pytest.raises(ValueError, match="not owned"):
        fresh.recover_session(session_id)


def test_deleted_child_is_not_resurrected(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("task", name="kid")
    assert host.collect([handle], timeout_ms=5000)[0].status == "done"
    session_id = host.list_subagents()[0].session_id
    host.delete_subagent(handle)
    fresh = _host(tmp_path)
    assert fresh.list_subagents() == []
    with pytest.raises(ValueError, match="deleted"):
        fresh.recover_session(session_id)


def test_rename_persists_lifecycle_name(tmp_path):
    host = _host(tmp_path)
    handle = host.spawn("task", name="kid")
    host.rename(handle, "renamed-kid")
    session_id = host.list_subagents()[0].session_id
    document = load_session(tmp_path, session_id)
    assert document["metadata"]["name"] == "renamed-kid"
    assert host.collect(timeout_ms=5000)[0].status == "done"
    fresh = _host(tmp_path)
    assert [row.session_name for row in fresh.list_subagents()] == ["renamed-kid"]


def test_terminal_storage_failure_is_error_never_done(tmp_path, monkeypatch):
    real_save = rlm_module.save_session
    calls: list = []

    def flaky(directory, session_id, messages, metadata=None):
        status = metadata.get("status") if isinstance(metadata, dict) else None
        calls.append(status)
        if len(calls) > 1:
            raise OSError("disk gone")
        return real_save(directory, session_id, messages, metadata)

    monkeypatch.setattr(rlm_module, "save_session", flaky)
    host = _host(tmp_path)
    host.spawn("task", name="kid")
    results = host.collect(timeout_ms=5000)
    assert results[0].status == "error"
    assert results[0].settled is True
    assert "durable save failed" in (results[0].error or "")
    assert "disk gone" in (results[0].error or "")


def test_delayed_terminal_write_cannot_resurrect_deleted_child(tmp_path, monkeypatch):
    finish = threading.Event()
    tombstone_entered = threading.Event()
    release_tombstone = threading.Event()
    late_write_done = threading.Event()
    real_save = rlm_module.save_session
    statuses: list[str] = []

    def runner(prompt, model=None, thinking=None):
        if not finish.wait(5):
            raise RuntimeError("child release barrier expired")
        return "private answer"

    def gated_save(directory, session_id, messages, metadata=None):
        statuses.append(metadata["status"])
        if len(statuses) == 2:
            # The delete's tombstone write: hold it while the child settles.
            tombstone_entered.set()
            if not release_tombstone.wait(5):
                raise RuntimeError("tombstone release barrier expired")
        path = real_save(directory, session_id, messages, metadata)
        if len(statuses) >= 3:
            late_write_done.set()
        return path

    monkeypatch.setattr(rlm_module, "save_session", gated_save)
    host = _host(tmp_path, runner=runner)
    try:
        handle = host.spawn("child-only task", name="kid")
        session_id = host.list_subagents()[0].session_id
        deleter = threading.Thread(target=host.delete_subagent, args=(handle,))
        deleter.start()
        assert tombstone_entered.wait(5)
        finish.set()
        release_tombstone.set()
        deleter.join(5)
        assert late_write_done.wait(5)
        document = load_session(tmp_path, session_id)
        assert document["metadata"]["status"] == "deleted"
        assert "private answer" not in json.dumps(document)
        fresh = _host(tmp_path)
        try:
            assert fresh.list_subagents() == []
        finally:
            fresh.shutdown()
    finally:
        finish.set()
        release_tombstone.set()
        host.shutdown()


def test_failed_tombstone_keeps_child_visible_and_collectable(tmp_path, monkeypatch):
    finish = threading.Event()

    def runner(prompt, model=None, thinking=None):
        if not finish.wait(5):
            raise RuntimeError("child release barrier expired")
        return "released answer"

    host = _host(tmp_path, runner=runner)
    persist = rlm_module.save_session

    def failed_delete(directory, session_id, messages, metadata=None):
        if metadata["status"] == "deleted":
            raise OSError("tombstone unavailable")
        return persist(directory, session_id, messages, metadata)

    try:
        handle = host.spawn("child-only task", name="kid")
        session_id = host.list_subagents()[0].session_id
        monkeypatch.setattr(rlm_module, "save_session", failed_delete)
        with pytest.raises(OSError, match="tombstone unavailable"):
            host.delete_subagent(handle)
        assert [row.rlm_child_id for row in host.list_subagents()] == [
            handle.rlm_child_id
        ]
        assert load_session(tmp_path, session_id)["metadata"]["status"] == "running"
        finish.set()
        result = host.collect([handle], timeout_ms=5000)[0]
        assert result.status == "done"
        assert result.answer_preview == "released answer"
        monkeypatch.setattr(rlm_module, "save_session", persist)
        assert host.delete_subagent(handle)["deleted"] == handle.rlm_child_id
        fresh = _host(tmp_path)
        try:
            assert fresh.list_subagents() == []
        finally:
            fresh.shutdown()
    finally:
        finish.set()
        host.shutdown()


# --- parent contract, recovery, tombstones, admission (phase 61 review) -------------


def _agent_parent(session_dir, **options):
    return OmegaPrimeAgent(
        ScriptedModel([]),
        registry=ToolRegistry(),
        session_dir=session_dir,
        **options,
    )


def test_real_agent_parent_writes_only_under_its_session_dir(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    session_dir = tmp_path / "sess"
    host = RlmHost(_agent_parent(session_dir), run_child=_scripted_runner())
    handle = host.spawn("real parent task", name="kid")
    assert host.collect([handle], timeout_ms=5000)[0].status == "done"
    session_id = host.list_subagents()[0].session_id
    assert session_id is not None
    document = load_session(session_dir, session_id)
    assert document["messages"][0] == {"role": "user", "content": "real parent task"}
    assert handle.session_dir.parent == session_dir / "rlm-children"
    assert list(cwd.iterdir()) == []


def test_real_agent_parent_at_max_depth_cannot_spawn(tmp_path):
    session_dir = tmp_path / "sess"
    agent = _agent_parent(session_dir, delegate_depth=2, max_depth=2)
    host = RlmHost(agent, run_child=_scripted_runner())
    with pytest.raises(ValueError, match="depth limit"):
        host.spawn("too deep", name="kid")
    assert not (session_dir / "sessions").exists()
    assert host.list_subagents() == []


def test_real_agent_parent_without_session_dir_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = OmegaPrimeAgent(ScriptedModel([]), registry=ToolRegistry())
    with pytest.raises(TypeError):
        RlmHost(agent, run_child=_scripted_runner())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "missing",
    ["session_dir", "session_name", "delegate_depth", "max_depth", "max_children"],
)
def test_parent_missing_contract_attribute_is_rejected(tmp_path, missing):
    parent = _Parent(tmp_path)
    delattr(parent, missing)
    with pytest.raises(TypeError):
        RlmHost(parent, run_child=_scripted_runner())


def test_parent_with_retired_depth_attribute_is_rejected(tmp_path):
    parent = _Parent(tmp_path)
    del parent.delegate_depth
    vars(parent)["depth"] = 0
    with pytest.raises(TypeError):
        RlmHost(parent, run_child=_scripted_runner())


def test_recovery_does_not_rewrite_settled_records_or_fail_on_write_error(
    tmp_path, monkeypatch
):
    host = _host(tmp_path)
    host.spawn("recover me", name="kid")
    assert host.collect(timeout_ms=5000)[0].status == "done"
    session_id = host.list_subagents()[0].session_id
    host.shutdown()
    stored = tmp_path / "sessions" / f"{session_id}.json"
    before = stored.read_bytes()

    def unwritable(directory, session_id, messages, metadata=None):
        raise OSError("read-only session dir")

    monkeypatch.setattr(rlm_module, "save_session", unwritable)
    fresh = _host(tmp_path)
    try:
        rows = fresh.list_subagents()
        assert [row.session_id for row in rows] == [session_id]
        assert rows[0].status == "completed"
        result = fresh.collect(timeout_ms=1000)[0]
        assert result.status == "done"
        assert "child done: recover me" in (result.answer_preview or "")
    finally:
        fresh.shutdown()
    assert stored.read_bytes() == before


def test_interrupted_record_recovers_as_error_even_when_write_fails(
    tmp_path, monkeypatch
):
    gate = threading.Event()

    def hanging(prompt, model=None, thinking=None):
        gate.wait(10.0)
        return "late answer"

    host = _host(tmp_path, runner=hanging)
    try:
        host.spawn("unfinished", name="kid")
        host.shutdown()

        def unwritable(directory, session_id, messages, metadata=None):
            raise OSError("disk full")

        monkeypatch.setattr(rlm_module, "save_session", unwritable)
        fresh = _host(tmp_path)
        try:
            rows = fresh.list_subagents()
            assert [row.status for row in rows] == ["error"]
            result = fresh.collect(timeout_ms=1000)[0]
            assert result.status == "error"
            assert result.settled is True
            assert "disk full" in (result.error or "")
        finally:
            fresh.shutdown()
    finally:
        gate.set()


def test_deleted_child_file_keeps_neither_prompt_nor_answer(tmp_path):
    host = _host(tmp_path, runner=_scripted_runner(answer="secret-answer"))
    handle = host.spawn("secret-prompt", name="kid")
    assert host.collect([handle], timeout_ms=5000)[0].status == "done"
    session_id = host.list_subagents()[0].session_id
    host.delete_subagent(handle)
    text = (tmp_path / "sessions" / f"{session_id}.json").read_text(encoding="utf-8")
    assert "secret-prompt" not in text
    assert "secret-answer" not in text
    fresh = _host(tmp_path)
    try:
        assert fresh.list_subagents() == []
        with pytest.raises(ValueError, match="deleted"):
            fresh.recover_session(session_id)
    finally:
        fresh.shutdown()


@pytest.mark.parametrize("fails", [False, True])
def test_collect_of_unsettled_child_reports_no_answer_or_error(
    tmp_path, monkeypatch, fails
):
    release_runner = threading.Event()
    terminal_entered = threading.Event()
    release_terminal = threading.Event()
    real_save = rlm_module.save_session

    def gated_save(directory, session_id, messages, metadata=None):
        if metadata["status"] in ("completed", "error"):
            terminal_entered.set()
            if not release_terminal.wait(5):
                raise RuntimeError("terminal release barrier expired")
        return real_save(directory, session_id, messages, metadata)

    def runner(prompt, model=None, thinking=None):
        if not release_runner.wait(5):
            raise RuntimeError("runner release barrier expired")
        if fails:
            raise RuntimeError("child exploded")
        return "answer text"

    monkeypatch.setattr(rlm_module, "save_session", gated_save)
    host = _host(tmp_path, runner=runner)
    try:
        host.spawn("task", name="kid")
        release_runner.set()
        assert terminal_entered.wait(5)
        pending = host.collect(timeout_ms=50)[0]
        assert pending.status == "running"
        assert pending.settled is False
        assert pending.answer_preview is None
        assert pending.error is None
        # Registry reads never wait on the in-flight terminal write.
        assert [row.status for row in host.list_subagents()] == ["running"]
        release_terminal.set()
        final = host.collect(timeout_ms=5000)[0]
        assert final.status == ("error" if fails else "done")
        assert final.settled is True
        if fails:
            assert "child exploded" in (final.error or "")
        else:
            assert final.answer_preview == "answer text"
    finally:
        release_runner.set()
        release_terminal.set()
        host.shutdown()


def test_concurrent_spawns_of_one_name_admit_exactly_one(tmp_path):
    host = _host(tmp_path, max_children=32)
    attackers = 6
    try:
        for round_index in range(10):
            name = f"same-{round_index}"
            start = threading.Barrier(attackers)
            outcomes: list[str] = []

            def attempt(name=name, start=start, outcomes=outcomes):
                start.wait(5)
                try:
                    host.spawn("task", name=name)
                except ValueError:
                    outcomes.append("refused")
                else:
                    outcomes.append("admitted")

            threads = [threading.Thread(target=attempt) for _ in range(attackers)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(10)
            assert outcomes.count("admitted") == 1
            assert outcomes.count("refused") == attackers - 1
            assert [row.session_name for row in host.list_subagents()].count(name) == 1
    finally:
        host.shutdown()


class _Roster:
    """Session-store stand-in: records every roster row create() is asked for."""

    def __init__(self):
        self.rows = []

    def create(self, *, session_id, name, prompt):
        self.rows.append((session_id, name, prompt))


@pytest.mark.parametrize("refusal", ["duplicate-name", "child-limit"])
def test_refused_create_session_leaves_no_roster_record(tmp_path, refusal):
    host = _host(tmp_path, max_children=1 if refusal == "child-limit" else 4)
    host.spawn("first", name="taken")
    roster = _Roster()
    name = "taken" if refusal == "duplicate-name" else "other"
    with pytest.raises(ValueError):
        host.create_session("second", name=name, session_store=roster)
    assert roster.rows == []
    assert [row.session_name for row in host.list_subagents()] == ["taken"]


def test_failed_roster_create_leaves_no_admitted_child(tmp_path):
    class _BrokenRoster:
        def create(self, *, session_id, name, prompt):
            raise OSError("roster unavailable")

    host = _host(tmp_path)
    with pytest.raises(OSError, match="roster unavailable"):
        host.create_session("task", name="kid", session_store=_BrokenRoster())
    assert host.list_subagents() == []
    fresh = _host(tmp_path)
    try:
        assert fresh.list_subagents() == []
    finally:
        fresh.shutdown()
