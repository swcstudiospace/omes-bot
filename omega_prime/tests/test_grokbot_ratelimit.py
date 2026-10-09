# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Phase 63-04: rate limiter, auth-failure throttle, middleware, tool interceptor."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from omega_prime.grokbot import ratelimit
from omega_prime.grokbot.interceptors import (
    ToolCall,
    ToolCallInterceptor,
    ToolOutcome,
    run_tool_call,
)
from omega_prime.grokbot.ratelimit import (
    AuthFailureThrottle,
    AuthThrottleMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    ToolRateLimitInterceptor,
)
from omega_prime.grokbot.security import SCOPE_CALL, Principal


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# --- RateLimiter -------------------------------------------------------------


def test_burst_then_denied_with_retry_after() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, burst=3, clock=clock)
    assert [limiter.acquire("a") for _ in range(3)] == [None, None, None]
    wait = limiter.acquire("a")
    assert wait == pytest.approx(1.0)  # 60/min = 1 token per second


def test_refill_is_smooth_and_capped_at_capacity() -> None:
    clock = FakeClock()
    limiter = RateLimiter(120, burst=2, clock=clock)  # 2 tokens per second
    assert limiter.acquire("a") is None
    assert limiter.acquire("a") is None
    wait = limiter.acquire("a")
    assert wait == pytest.approx(0.5)
    clock.advance(0.5)
    assert limiter.acquire("a") is None
    assert limiter.acquire("a") == pytest.approx(0.5)
    clock.advance(3600)  # long idle never banks more than `burst`
    assert [limiter.acquire("a") for _ in range(2)] == [None, None]
    assert limiter.acquire("a") is not None


def test_partial_wait_shrinks_as_time_passes() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, burst=1, clock=clock)
    assert limiter.acquire("a") is None
    clock.advance(0.25)
    assert limiter.acquire("a") == pytest.approx(0.75)


def test_default_burst_is_the_per_minute_limit() -> None:
    limiter = RateLimiter(5, clock=FakeClock())
    assert [limiter.acquire("a") for _ in range(5)] == [None] * 5
    assert limiter.acquire("a") is not None


def test_keys_are_independent() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    assert limiter.acquire("a") is None
    assert limiter.acquire("a") is not None
    assert limiter.acquire("b") is None


def test_global_tier_denies_across_keys_without_spending_key_tokens() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, 2, burst=1, clock=clock)  # global: 2 tokens, 1 per 30s
    assert limiter.acquire("a") is None
    assert limiter.acquire("b") is None
    assert limiter.acquire("c") == pytest.approx(30.0)
    # "c" was denied by the global tier, so its own bucket is still full: had the
    # denial spent a key token, c (1 token per 60s) would still be short at 30s.
    clock.advance(30.0)
    assert limiter.acquire("c") is None


def test_key_denial_does_not_consume_global_tokens() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, 3, burst=1, clock=clock)
    assert limiter.acquire("a") is None  # global 3 -> 2
    for _ in range(10):  # denied by the key tier, global must stay at 2
        assert limiter.acquire("a") is not None
    assert limiter.acquire("b") is None  # global 2 -> 1
    assert limiter.acquire("c") is None  # global 1 -> 0
    assert limiter.acquire("d") is not None


def test_wait_is_the_slower_of_the_two_tiers() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, 1, burst=1, clock=clock)  # global refills 1 / 60s
    assert limiter.acquire("a") is None
    assert limiter.acquire("a") == pytest.approx(60.0)  # global is slower than key


def test_disabled_tiers() -> None:
    clock = FakeClock()
    off = RateLimiter(0, clock=clock)
    assert not off.enabled
    assert all(off.acquire("a") is None for _ in range(1000))
    assert off.tracked_keys() == 0

    only_global = RateLimiter(0, 2, clock=clock)
    assert only_global.acquire("a") is None
    assert only_global.acquire("b") is None
    assert only_global.acquire("c") is not None
    assert only_global.tracked_keys() == 0

    only_key = RateLimiter(60, 0, burst=1, clock=clock)
    assert only_key.acquire("a") is None
    assert only_key.acquire("a") is not None


def test_invalid_configuration_rejected() -> None:
    with pytest.raises(ValueError):
        RateLimiter(-1)
    with pytest.raises(ValueError):
        RateLimiter(10, -1)
    with pytest.raises(ValueError):
        RateLimiter(10, burst=0)


def test_key_buckets_are_lru_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ratelimit, "MAX_TRACKED_KEYS", 3)
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    for key in ("a", "b", "c"):
        assert limiter.acquire(key) is None
    assert limiter.acquire("a") is not None  # touch a: b is now least recent
    assert limiter.acquire("d") is None  # evicts b
    assert limiter.tracked_keys() == 3
    assert limiter.acquire("b") is None  # evicted: starts with a full bucket
    assert limiter.acquire("a") is not None  # a was kept (c was evicted instead)
    assert limiter.tracked_keys() == 3


def test_acquire_is_thread_safe() -> None:
    limiter = RateLimiter(60, burst=100, clock=FakeClock())
    results: list[float | None] = []
    lock = threading.Lock()

    def worker() -> None:
        local = [limiter.acquire("shared") for _ in range(50)]
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(1 for r in results if r is None) == 100


# --- RateLimitMiddleware ------------------------------------------------------


class _SetPrincipal:
    """Stand-in for AuthMiddleware: attaches a principal chosen by header."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            for key, value in scope.get("headers", ()):
                if key == b"x-principal":
                    scope.setdefault("state", {})["principal"] = Principal(
                        value.decode(), frozenset({SCOPE_CALL})
                    )
        await self.app(scope, receive, send)


async def _ok(request: Request) -> Any:
    return PlainTextResponse("ok")


def _app() -> Starlette:
    return Starlette(
        routes=[Route(p, _ok) for p in ("/", "/healthz", "/readyz", "/other")]
    )


def _wrap(inner: Any, *layers: Any) -> Any:
    app = inner
    for layer in reversed(layers):
        app = layer(app)
    return app


def test_middleware_keys_by_principal_and_429_shape() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    events: list[dict[str, Any]] = []
    app = _wrap(
        _app(),
        _SetPrincipal,
        lambda inner: RateLimitMiddleware(
            inner, limiter=limiter, on_limited=events.append
        ),
    )
    client = TestClient(app)
    assert client.get("/", headers={"x-principal": "alice"}).status_code == 200
    denied = client.get("/", headers={"x-principal": "alice"})
    assert denied.status_code == 429
    assert denied.json() == {"error": "rate_limited", "retry_after": 1}
    assert denied.headers["retry-after"] == "1"
    # A different principal has its own bucket.
    assert client.get("/", headers={"x-principal": "bob"}).status_code == 200
    assert events == [{"key": "alice", "path": "/", "retry_after": pytest.approx(1.0)}]


def test_middleware_keys_by_client_host_without_principal() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    events: list[dict[str, Any]] = []
    app = _wrap(
        _app(),
        lambda inner: RateLimitMiddleware(
            inner, limiter=limiter, on_limited=events.append
        ),
    )
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 429
    assert events[0]["key"] == "testclient"
    assert set(events[0]) == {"key", "path", "retry_after"}


def test_middleware_exempt_paths_never_limited_or_counted() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    app = _wrap(_app(), lambda i: RateLimitMiddleware(i, limiter=limiter))
    client = TestClient(app)
    for _ in range(5):
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200
    assert client.get("/other").status_code == 200  # token untouched by probes
    assert client.get("/other").status_code == 429


def test_middleware_retry_after_rounds_up() -> None:
    clock = FakeClock()
    limiter = RateLimiter(20, burst=1, clock=clock)  # one token per 3 s
    app = _wrap(_app(), lambda i: RateLimitMiddleware(i, limiter=limiter))
    client = TestClient(app)
    assert client.get("/").status_code == 200
    clock.advance(0.5)
    denied = client.get("/")
    assert denied.headers["retry-after"] == "3"  # ceil(2.5)
    assert denied.json()["retry_after"] == 3


def test_middleware_swallows_callback_exceptions() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())

    def explode(event: dict[str, Any]) -> None:
        del event
        raise RuntimeError("callback failed")

    app = _wrap(
        _app(),
        lambda i: RateLimitMiddleware(i, limiter=limiter, on_limited=explode),
    )
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 429


def test_middleware_ignores_non_http_scopes() -> None:
    seen: list[str] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        seen.append(scope["type"])

    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    middleware = RateLimitMiddleware(inner, limiter=limiter)

    async def run() -> None:
        for _ in range(3):
            await middleware({"type": "lifespan"}, None, None)

    asyncio.run(run())
    assert seen == ["lifespan"] * 3


# --- AuthFailureThrottle ------------------------------------------------------


def test_throttle_blocks_at_threshold_and_window_slides() -> None:
    clock = FakeClock()
    throttle = AuthFailureThrottle(3, 60.0, clock=clock)
    assert throttle.blocked("1.2.3.4") is None
    throttle.record("1.2.3.4")  # t=0
    clock.advance(10)
    throttle.record("1.2.3.4")  # t=10
    assert throttle.blocked("1.2.3.4") is None
    clock.advance(10)
    throttle.record("1.2.3.4")  # t=20
    assert throttle.blocked("1.2.3.4") == pytest.approx(40.0)  # t=0 leaves at 60
    clock.advance(40)  # t=60: the oldest failure has left the window
    assert throttle.blocked("1.2.3.4") is None
    throttle.record("1.2.3.4")  # t=60: counted failures are t=10,20,60
    assert throttle.blocked("1.2.3.4") == pytest.approx(10.0)


def test_throttle_clients_are_independent_and_unblock_after_window() -> None:
    clock = FakeClock()
    throttle = AuthFailureThrottle(1, 30.0, clock=clock)
    throttle.record("a")
    assert throttle.blocked("a") == pytest.approx(30.0)
    assert throttle.blocked("b") is None
    clock.advance(30)
    assert throttle.blocked("a") is None
    assert throttle.tracked_clients() == 0  # expired entries are dropped


def test_throttle_disabled_and_validation() -> None:
    throttle = AuthFailureThrottle(0, clock=FakeClock())
    assert not throttle.enabled
    for _ in range(100):
        throttle.record("a")
    assert throttle.blocked("a") is None
    assert throttle.tracked_clients() == 0
    with pytest.raises(ValueError):
        AuthFailureThrottle(-1)
    with pytest.raises(ValueError):
        AuthFailureThrottle(1, 0.0)


def test_throttle_memory_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ratelimit, "MAX_TRACKED_CLIENTS", 4)
    throttle = AuthFailureThrottle(2, 60.0, clock=FakeClock())
    for index in range(10):
        throttle.record(f"c{index}")
    assert throttle.tracked_clients() == 4
    for _ in range(50):  # per-client history never exceeds max_failures
        throttle.record("c9")
    assert throttle.blocked("c9") is not None
    assert len(throttle._failures["c9"]) == 2


# --- AuthThrottleMiddleware ---------------------------------------------------


def test_throttle_middleware_blocks_before_auth_and_exempts_probes() -> None:
    clock = FakeClock()
    throttle = AuthFailureThrottle(2, 60.0, clock=clock)
    reached: list[str] = []

    async def downstream(request: Request) -> Any:
        reached.append(request.url.path)
        return JSONResponse({"ok": True})

    inner = Starlette(
        routes=[Route(p, downstream) for p in ("/", "/healthz", "/readyz")]
    )
    app = _wrap(inner, lambda i: AuthThrottleMiddleware(i, throttle=throttle))
    client = TestClient(app)
    assert client.get("/").status_code == 200
    throttle.record("testclient")
    throttle.record("testclient")
    blocked = client.get("/")
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"
    assert blocked.json()["retry_after"] == 60
    assert reached == ["/"]  # the blocked request never reached the app
    assert client.get("/healthz").status_code == 200
    clock.advance(60)
    assert client.get("/").status_code == 200


# --- ToolRateLimitInterceptor -------------------------------------------------


def _tool_call(principal: Principal | None) -> ToolCall:
    return ToolCall("tool_x", {}, principal)


def test_tool_interceptor_denial_shape_and_principal_keys() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    interceptor = ToolRateLimitInterceptor(limiter)
    alice = Principal("alice", frozenset({SCOPE_CALL}))
    assert interceptor.before(_tool_call(alice)) is None
    denial = interceptor.before(_tool_call(alice))
    assert denial is not None
    assert denial.code == "rate_limited"
    assert denial.retry_after == pytest.approx(1.0)
    assert "1s" in denial.message
    # No principal means the local operator, with its own bucket.
    assert interceptor.before(_tool_call(None)) is None
    assert interceptor.before(_tool_call(None)) is not None
    assert interceptor.before(_tool_call(Principal("bob", frozenset()))) is None


def test_tool_interceptor_in_run_tool_call_chain() -> None:
    limiter = RateLimiter(60, burst=1, clock=FakeClock())
    interceptor = ToolRateLimitInterceptor(limiter)
    after_calls: list[ToolOutcome] = []
    dispatched: list[int] = []

    class Tail:
        def before(self, call: ToolCall) -> None:
            del call

        def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
            del call
            after_calls.append(outcome)

    def dispatch() -> str:
        dispatched.append(1)
        return json.dumps({"result": 1})

    chain: list[ToolCallInterceptor] = [interceptor, Tail()]
    payload, outcome = run_tool_call(chain, _tool_call(None), dispatch)
    assert outcome.status == "ok" and json.loads(payload) == {"result": 1}
    payload, outcome = run_tool_call(chain, _tool_call(None), dispatch)
    assert outcome.status == "denied"
    assert outcome.denial_code == "rate_limited"
    assert json.loads(payload)["error"].startswith("rate_limited:")
    assert dispatched == [1]  # denied call never dispatched
    interceptor.after(_tool_call(None), outcome)  # after is a no-op
    assert len(after_calls) == 1  # Tail.before never ran for the denied call
