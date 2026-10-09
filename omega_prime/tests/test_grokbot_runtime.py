# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Phase 62-01: fail-closed runtime loader and interceptor plumbing."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from omega_prime.grokbot.interceptors import (
    InFlightInterceptor,
    ScopeInterceptor,
    ToolCall,
    ToolDenial,
    ToolOutcome,
)
from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.security import SCOPE_CALL, SCOPE_READ, Principal
from omega_prime.mcp_server import (
    SERVER_NAME,
    Runtime,
    RuntimeConfigError,
    ToolGate,
    build_server,
    call_tool_handler,
    list_tools_handler,
    load_runtime,
)
from omega_prime.tools.registry import ToolRegistry

READER = Principal("reader", frozenset({SCOPE_READ}))
CALLER = Principal("caller", frozenset({SCOPE_CALL}))


class Params:
    def __init__(self, name: str, arguments: Any = None) -> None:
        self.name = name
        self.arguments = arguments


def _ctx(principal: Principal | None, request_id: str | None = None) -> Any:
    state = SimpleNamespace(principal=principal, request_id=request_id)
    return SimpleNamespace(request=SimpleNamespace(state=state))


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "echo",
        "echo the text",
        {"type": "object", "properties": {"text": {"type": "string"}}},
        lambda text="": {"echo": text},
    )
    registry.register(
        "gated",
        "needs approval",
        {"type": "object", "properties": {}},
        lambda: {"ran": True},
        requires_approval=True,
    )
    return registry


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    shutil.copytree(
        find_repo_root() / "omega_prime" / "contracts",
        tmp_path / "omega_prime" / "contracts",
    )
    return tmp_path


def test_load_runtime_matches_list_tools(tmp_path: Path):
    before = dict(os.environ)
    runtime = load_runtime(find_repo_root(), tmp_path / "home", env={})
    assert isinstance(runtime, Runtime)
    assert runtime.roster
    listed = asyncio.run(
        list_tools_handler(runtime.registry, runtime.roster)(None, None)
    )
    assert runtime.tool_names == [tool.name for tool in listed.tools]
    assert set(runtime.tool_names) <= set(runtime.roster)
    assert set(runtime.gated_tools) <= set(runtime.tool_names)
    assert all(runtime.registry.approval_required(n) for n in runtime.gated_tools)
    assert runtime.approval_log is runtime.registry._approval_log
    assert dict(os.environ) == before


def test_load_runtime_no_roster_serves_every_registered_tool(tmp_path: Path):
    runtime = load_runtime(find_repo_root(), tmp_path / "home", no_roster=True, env={})
    assert runtime.roster is None
    registered = [s["function"]["name"] for s in runtime.registry.schemas()]
    assert runtime.tool_names == registered


def test_load_runtime_missing_roster_fails_closed(repo_copy: Path):
    roster = repo_copy / "omega_prime/contracts/tool-rosters/omega-prime.yaml"
    roster.unlink()
    with pytest.raises(RuntimeConfigError, match="cannot read roster") as info:
        load_runtime(repo_copy, repo_copy / "home", env={})
    assert "\n" not in str(info.value)
    # an explicit no-roster opt-out is the only way past a missing roster
    assert load_runtime(repo_copy, repo_copy / "home", no_roster=True, env={})


def test_load_runtime_empty_roster_fails_closed(repo_copy: Path):
    roster = repo_copy / "omega_prime/contracts/tool-rosters/omega-prime.yaml"
    roster.write_text("tools:\n", encoding="utf-8")
    with pytest.raises(RuntimeConfigError, match="lists no tools"):
        load_runtime(repo_copy, repo_copy / "home", env={})


def test_load_runtime_corrupt_policy_fails_closed(repo_copy: Path):
    policy = repo_copy / "omega_prime/contracts/policies/omega-prime.json"
    policy.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeConfigError, match="cannot load seat policy"):
        load_runtime(repo_copy, repo_copy / "home", env={})
    policy.unlink()
    with pytest.raises(RuntimeConfigError, match="cannot load seat policy"):
        load_runtime(repo_copy, repo_copy / "home", env={})


def test_load_runtime_refused_approval_fails_closed():
    root = find_repo_root()
    with pytest.raises(RuntimeConfigError, match="cannot pre-approve gated_tool"):
        load_runtime(
            root, None, approvals=[("gated_tool", "bot-00-omega-prime")], env={}
        )
    with pytest.raises(RuntimeConfigError, match="bad approval"):
        load_runtime(root, None, approvals=[("gated_tool", "")], env={})


def test_load_runtime_records_valid_approval(tmp_path: Path):
    runtime = load_runtime(
        find_repo_root(),
        tmp_path / "home",
        approvals=[("infra_railway_redeploy", "alice")],
        env={},
    )
    assert runtime.approval_log.is_approved("infra_railway_redeploy")
    assert "infra_railway_redeploy" in runtime.gated_tools


def test_call_tool_without_interceptors_is_unchanged():
    call = call_tool_handler(_registry(), ["echo"])
    ok = asyncio.run(call(None, Params("echo", {"text": "hi"})))
    assert ok.is_error in (False, None)
    assert json.loads(ok.content[0].text) == {"echo": "hi"}
    forbidden = asyncio.run(call(None, Params("gated")))
    assert forbidden.is_error is True
    assert json.loads(forbidden.content[0].text) == {
        "error": "policy forbids gated",
        "tool": "gated",
    }
    unknown = asyncio.run(call_tool_handler(_registry())(None, Params("nope")))
    assert unknown.is_error is True and "Unknown tool" in unknown.content[0].text
    gated = asyncio.run(call_tool_handler(_registry())(None, Params("gated", None)))
    assert gated.is_error is True and "approval required" in gated.content[0].text


def test_scope_interceptor_denies_read_only_principal():
    call = call_tool_handler(_registry(), interceptors=[ScopeInterceptor()])
    denied = asyncio.run(call(_ctx(READER), Params("echo", {"text": "hi"})))
    assert denied.is_error is True
    assert json.loads(denied.content[0].text) == {
        "error": f"forbidden: principal reader lacks the {SCOPE_CALL} scope",
        "tool": "echo",
    }
    allowed = asyncio.run(call(_ctx(CALLER), Params("echo", {"text": "hi"})))
    assert allowed.is_error in (False, None)
    assert json.loads(allowed.content[0].text) == {"echo": "hi"}
    stdio = asyncio.run(call(None, Params("echo", {"text": "local"})))
    assert json.loads(stdio.content[0].text) == {"echo": "local"}


def test_denied_call_is_not_dispatched():
    registry = _registry()
    hits: list[str] = []

    def probe() -> dict[str, bool]:
        hits.append("run")
        return {"ok": True}

    registry.register(
        "probe",
        "records invocations",
        {"type": "object", "properties": {}},
        probe,
    )
    call = call_tool_handler(registry, interceptors=[ScopeInterceptor()])
    asyncio.run(call(_ctx(READER), Params("probe")))
    assert hits == []
    asyncio.run(call(_ctx(CALLER), Params("probe")))
    assert hits == ["run"]


class Spy:
    def __init__(self, deny: bool = False) -> None:
        self.deny = deny
        self.calls: list[ToolCall] = []
        self.outcomes: list[ToolOutcome] = []

    def before(self, call: ToolCall) -> ToolDenial | None:
        self.calls.append(call)
        return ToolDenial("circuit_open", "paused") if self.deny else None

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call
        self.outcomes.append(outcome)


def test_handler_threads_transport_principal_and_request_id():
    spy = Spy()
    call = call_tool_handler(_registry(), interceptors=[spy], transport="sse")
    asyncio.run(call(_ctx(CALLER, "req-1"), Params("echo", {"text": "x"})))
    (seen,) = spy.calls
    assert (seen.name, seen.transport) == ("echo", "sse")
    assert seen.principal is CALLER and seen.request_id == "req-1"
    assert seen.arguments == {"text": "x"}
    assert spy.outcomes[0].status == "ok"


def test_roster_denial_is_observed_by_interceptors():
    spy = Spy()
    call = call_tool_handler(_registry(), ["echo"], interceptors=[spy])
    result = asyncio.run(call(None, Params("gated")))
    assert result.is_error is True
    assert json.loads(result.content[0].text)["error"] == "policy forbids gated"
    assert spy.outcomes[0].is_error


def test_interceptor_error_and_inflight_via_handler():
    inflight = InFlightInterceptor()
    deny = Spy(deny=True)
    call = call_tool_handler(_registry(), interceptors=[inflight, deny])
    result = asyncio.run(call(None, Params("echo", {})))
    assert result.is_error is True
    assert "circuit_open: paused" in result.content[0].text
    assert inflight.count == 0


def test_build_server_accepts_interceptors_and_transport():
    server = build_server(
        _registry(), ["echo"], interceptors=[ScopeInterceptor()], transport="http"
    )
    assert server.name == SERVER_NAME


_NO_ARGS = {"type": "object", "properties": {}}


def test_tool_runs_off_the_event_loop():
    """A blocked tool must not freeze the loop (health, keepalives, shutdown)."""
    release = threading.Event()
    started = threading.Event()
    registry = ToolRegistry()

    def block() -> dict[str, bool]:
        started.set()
        # A timeout turns a regression (tool on the loop thread) into a failure
        # instead of a hang: the loop could never reach release.set().
        return {"released": release.wait(timeout=5)}

    registry.register("block", "waits for a release", _NO_ARGS, block)
    call = call_tool_handler(registry)

    async def scenario() -> tuple[int, Any]:
        task = asyncio.create_task(call(None, Params("block")))
        while not started.is_set():
            await asyncio.sleep(0.005)
        beats = 0
        for _ in range(5):
            await asyncio.sleep(0.01)  # the loop keeps turning while the tool blocks
            beats += 1
        release.set()
        return beats, await task

    beats, result = asyncio.run(scenario())
    assert beats == 5
    assert json.loads(result.content[0].text) == {"released": True}


class _Overlap:
    """A tool body that records how many calls ran at the same time."""

    def __init__(self, barrier: threading.Barrier | None = None) -> None:
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.barrier = barrier

    def __call__(self) -> dict[str, bool]:
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            if self.barrier is not None:
                self.barrier.wait()
            else:
                time.sleep(0.02)
        finally:
            with self.lock:
                self.active -= 1
        return {"ok": True}


def test_tool_calls_are_serialized_by_default():
    tracker = _Overlap()
    registry = ToolRegistry()
    registry.register("work", "tracks overlap", _NO_ARGS, tracker)
    call = call_tool_handler(registry)

    async def burst() -> list[Any]:
        return list(
            await asyncio.gather(*(call(None, Params("work")) for _ in range(4)))
        )

    results = asyncio.run(burst())
    assert tracker.peak == 1
    assert all(not r.is_error for r in results)


def test_gate_limit_allows_that_many_concurrent_calls():
    # Both calls must be inside the tool at once for the barrier to open.
    tracker = _Overlap(threading.Barrier(2, timeout=5))
    registry = ToolRegistry()
    registry.register("work", "tracks overlap", _NO_ARGS, tracker)
    call = call_tool_handler(registry, gate=ToolGate(limit=2))

    async def pair() -> list[Any]:
        return list(
            await asyncio.gather(call(None, Params("work")), call(None, Params("work")))
        )

    results = asyncio.run(pair())
    assert tracker.peak == 2
    assert all(not r.is_error for r in results)


def test_tool_may_start_its_own_event_loop():
    registry = ToolRegistry()

    def uses_asyncio_run() -> dict[str, bool]:
        asyncio.run(asyncio.sleep(0))  # RuntimeError when called on a running loop
        return {"ok": True}

    registry.register("loopy", "starts its own loop", _NO_ARGS, uses_asyncio_run)
    result = asyncio.run(call_tool_handler(registry)(None, Params("loopy")))
    assert result.is_error is False
    assert json.loads(result.content[0].text) == {"ok": True}


def test_gate_reuse_across_event_loops_and_bad_limit():
    gate = ToolGate()
    registry = _registry()
    call = call_tool_handler(registry, gate=gate)
    for _ in range(2):  # a gate outlives one asyncio.run
        result = asyncio.run(call(None, Params("echo", {"text": "hi"})))
        assert json.loads(result.content[0].text) == {"echo": "hi"}
    with pytest.raises(ValueError, match="at least 1"):
        ToolGate(limit=0)
