# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Phase 62-01: tool-call interceptors."""

from __future__ import annotations

import hashlib
import json
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from omega_prime.grokbot.interceptors import (
    AuditInterceptor,
    InFlightInterceptor,
    ScopeInterceptor,
    ToolCall,
    ToolDenial,
    ToolOutcome,
    call_from_context,
    run_tool_call,
)
from omega_prime.grokbot.security import (
    SCOPE_CALL,
    SCOPE_READ,
    Principal,
)

READER = Principal("reader", frozenset({SCOPE_READ}))
CALLER = Principal("caller", frozenset({SCOPE_CALL}))


def _call(principal: Principal | None = None, **arguments: Any) -> ToolCall:
    return ToolCall("tool_x", arguments, principal, transport="sse", request_id="r1")


class Recorder:
    """Interceptor that logs its before/after order into a shared list."""

    def __init__(
        self,
        name: str,
        log: list[str],
        *,
        deny: ToolDenial | None = None,
        raise_before: bool = False,
        raise_after: bool = False,
    ) -> None:
        self.name, self.log, self.deny = name, log, deny
        self.raise_before, self.raise_after = raise_before, raise_after
        self.outcomes: list[ToolOutcome] = []

    def before(self, call: ToolCall) -> ToolDenial | None:
        self.log.append(f"before:{self.name}")
        if self.raise_before:
            raise RuntimeError("boom")
        return self.deny

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        self.log.append(f"after:{self.name}")
        self.outcomes.append(outcome)
        if self.raise_after:
            raise RuntimeError("after boom")


def test_chain_order_and_dispatch():
    log: list[str] = []
    chain = [Recorder("a", log), Recorder("b", log)]

    def dispatch() -> str:
        log.append("dispatch")
        return json.dumps({"ok": True})

    payload, outcome = run_tool_call(chain, _call(), dispatch)
    assert json.loads(payload) == {"ok": True}
    assert outcome.status == "ok" and not outcome.is_error
    assert outcome.denial_code is None and outcome.duration_ms >= 0
    assert log == ["before:a", "before:b", "dispatch", "after:a", "after:b"]


def test_no_interceptors_passes_payload_through():
    payload, outcome = run_tool_call((), _call(), lambda: "not json")
    assert payload == "not json"
    assert (outcome.status, outcome.is_error) == ("ok", False)


def test_error_payload_marks_error_but_null_error_is_ok():
    _, failed = run_tool_call((), _call(), lambda: json.dumps({"error": "bad"}))
    assert (failed.status, failed.is_error, failed.error) == ("error", True, "bad")
    _, loaded = run_tool_call((), _call(), lambda: json.dumps({"error": None}))
    assert (loaded.status, loaded.is_error) == ("ok", False)


def test_first_denial_stops_dispatch_and_after_balances():
    log: list[str] = []
    denial = ToolDenial("rate_limited", "slow down", retry_after=2.0)
    first = Recorder("a", log)
    second = Recorder("b", log, deny=denial)
    third = Recorder("c", log)

    def dispatch() -> str:
        raise AssertionError("must not dispatch")

    payload, outcome = run_tool_call([first, second, third], _call(), dispatch)
    assert json.loads(payload) == {
        "error": "rate_limited: slow down",
        "tool": "tool_x",
    }
    assert outcome.status == "denied" and outcome.is_error
    assert outcome.denial_code == "rate_limited"
    # the denier and those before it observe the outcome; later ones never ran
    assert log == ["before:a", "before:b", "after:a", "after:b"]
    assert third.outcomes == []
    assert second.outcomes[0] is outcome


def test_before_exception_is_interceptor_error_denial():
    log: list[str] = []
    chain = [Recorder("a", log), Recorder("b", log, raise_before=True)]
    payload, outcome = run_tool_call(chain, _call(), lambda: "never")
    assert outcome.status == "denied"
    assert outcome.denial_code == "interceptor_error"
    assert json.loads(payload)["error"].startswith("interceptor_error:")
    assert log == ["before:a", "before:b", "after:a", "after:b"]


def test_after_exception_is_swallowed_and_others_still_run():
    log: list[str] = []
    chain = [Recorder("a", log, raise_after=True), Recorder("b", log)]
    payload, outcome = run_tool_call(chain, _call(), lambda: json.dumps({"v": 1}))
    assert json.loads(payload) == {"v": 1} and outcome.status == "ok"
    assert log[-2:] == ["after:a", "after:b"]


def test_dispatch_exception_runs_after_then_propagates():
    log: list[str] = []
    recorder = Recorder("a", log)

    def dispatch() -> str:
        raise ValueError("kaput")

    with pytest.raises(ValueError, match="kaput"):
        run_tool_call([recorder], _call(), dispatch)
    assert log == ["before:a", "after:a"]
    assert recorder.outcomes[0].status == "error"
    assert recorder.outcomes[0].error == "ValueError: kaput"


def test_scope_interceptor_matrix():
    scope = ScopeInterceptor()
    assert scope.before(_call(None)) is None
    assert scope.before(_call(CALLER)) is None
    assert scope.before(_call(Principal("admin", frozenset({"admin"})))) is None
    denial = scope.before(_call(READER))
    assert denial is not None and denial.code == "forbidden"
    assert "reader" in denial.message
    payload, outcome = run_tool_call([scope], _call(READER), lambda: "never")
    assert outcome.denial_code == "forbidden"
    assert json.loads(payload)["tool"] == "tool_x"


class FakeTracer:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_event(self, event: str, **fields: Any) -> dict[str, Any]:
        record = {"event": event, **fields}
        self.events.append(record)
        return record


def test_audit_interceptor_digest_mode_stores_no_values():
    tracer = FakeTracer()
    audit = AuditInterceptor(tracer)
    secret = "super-secret-value-123"
    call = _call(CALLER, path=secret, mode="x")
    run_tool_call([audit], call, lambda: json.dumps({"ok": 1}))
    (event,) = tracer.events
    assert event["event"] == "tool_call"
    assert event["tool_name"] == "tool_x" and event["caller"] == "caller"
    assert event["status"] == "ok" and event["is_error"] is False
    details = event["details"]
    canonical = json.dumps(
        {"mode": "x", "path": secret},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert details["arg_keys"] == ["mode", "path"]
    assert details["args_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert details["transport"] == "sse" and details["request_id"] == "r1"
    assert details["denial"] is None and details["error"] is None
    assert secret not in json.dumps(event)
    assert "arguments" not in details


def test_audit_interceptor_local_caller_denial_and_error_preview():
    tracer = FakeTracer()
    audit = AuditInterceptor(tracer)
    # audit sits first so its `before` runs and it observes the later denial
    run_tool_call([audit, ScopeInterceptor()], _call(READER), lambda: "never")
    run_tool_call(
        [audit],
        _call(None),
        lambda: json.dumps({"error": "x" * 500 + " Bearer abcdefgh12345678"}),
    )
    denied, errored = tracer.events
    assert denied["status"] == "denied" and denied["details"]["denial"] == "forbidden"
    assert errored["caller"] == "local" and errored["status"] == "error"
    assert errored["is_error"] is True
    assert len(errored["details"]["error"]) <= 200


def test_audit_interceptor_redacted_mode_scrubs_secrets():
    tracer = FakeTracer()
    audit = AuditInterceptor(tracer, args_mode="redacted")
    call = _call(
        CALLER, api_key="sk-abcdefghijklmnopqrstuvwxyz", note="Bearer abc12345"
    )
    run_tool_call([audit], call, lambda: "{}")
    arguments = tracer.events[0]["details"]["arguments"]
    assert arguments["api_key"] == "[REDACTED]"
    assert "abc12345" not in arguments["note"]
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in json.dumps(tracer.events)
    with pytest.raises(ValueError):
        AuditInterceptor(tracer, args_mode="full")


def test_inflight_counter_balances_including_denial():
    inflight = InFlightInterceptor()
    seen: list[int] = []

    def dispatch() -> str:
        seen.append(inflight.count)
        return "{}"

    run_tool_call([inflight], _call(), dispatch)
    assert seen == [1] and inflight.count == 0
    run_tool_call(
        [inflight, Recorder("d", [], deny=ToolDenial("forbidden", "no"))],
        _call(),
        dispatch,
    )
    assert inflight.count == 0

    def explode() -> str:
        raise RuntimeError("dispatch failed")

    with pytest.raises(RuntimeError):
        run_tool_call([inflight], _call(), explode)
    assert inflight.count == 0


def test_inflight_counter_is_thread_safe():
    inflight = InFlightInterceptor()
    call = _call()

    def work() -> None:
        for _ in range(500):
            inflight.before(call)
            inflight.after(call, ToolOutcome("ok", False, 0.0))

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert inflight.count == 0


def test_call_from_context_variants():
    stdio = call_from_context(None, "t", None)
    assert stdio.principal is None and stdio.arguments == {}
    assert stdio.transport == "stdio" and stdio.request_id is None
    assert call_from_context(SimpleNamespace(request=None), "t", {}).principal is None

    state = SimpleNamespace(principal=CALLER, request_id="req-9")
    ctx = SimpleNamespace(request=SimpleNamespace(state=state))
    call = call_from_context(ctx, "t", {"a": 1}, transport="http")
    assert call.principal is CALLER and call.request_id == "req-9"
    assert call.transport == "http" and call.arguments == {"a": 1}

    bare = SimpleNamespace(request=SimpleNamespace(state=SimpleNamespace()))
    assert call_from_context(bare, "t", {}).principal is None
    assert call_from_context(None, "t", ["not", "a", "dict"]).arguments == {}
