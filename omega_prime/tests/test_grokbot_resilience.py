# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Phase 63-04: circuit breaker, failure classification, breaker interceptor."""

from __future__ import annotations

import json
import random
import threading

import pytest

from omega_prime.grokbot.interceptors import (
    ToolCall,
    ToolCallInterceptor,
    ToolDenial,
    ToolOutcome,
    run_tool_call,
)
from omega_prime.grokbot.resilience import (
    CircuitBreaker,
    ToolCircuitBreakerInterceptor,
    is_infrastructure_failure,
)


class FakeClock:
    def __init__(self, now: float = 500.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ExtremeRng(random.Random):
    """`uniform` returns an end of the requested range, for exact jitter tests."""

    def __init__(self, high: bool) -> None:
        super().__init__(0)
        self._high = high

    def uniform(self, a: float, b: float) -> float:
        return b if self._high else a


def _breaker(
    clock: FakeClock,
    *,
    failure_threshold: int = 5,
    cooldown_seconds: float = 30.0,
    half_open_max: int = 1,
) -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold,
        cooldown_seconds,
        jitter=0.0,
        half_open_max=half_open_max,
        clock=clock,
        rng=random.Random(7),
    )


# --- CircuitBreaker -------------------------------------------------------------


def test_closed_to_open_at_threshold() -> None:
    clock = FakeClock()
    breaker = _breaker(clock, failure_threshold=3, cooldown_seconds=30.0)
    assert breaker.state == "closed"
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "closed"
    assert breaker.allow() is None
    breaker.record_failure()
    assert breaker.state == "open"
    assert breaker.allow() == pytest.approx(30.0)
    clock.advance(10)
    assert breaker.allow() == pytest.approx(20.0)


def test_success_resets_consecutive_failures() -> None:
    breaker = _breaker(FakeClock(), failure_threshold=3)
    for _ in range(5):
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
    assert breaker.state == "closed"


def test_open_to_half_open_to_closed_on_probe_success() -> None:
    clock = FakeClock()
    breaker = _breaker(clock, failure_threshold=1, cooldown_seconds=30.0)
    breaker.record_failure()
    clock.advance(29.9)
    assert breaker.state == "open"
    assert breaker.allow() is not None
    clock.advance(0.1)
    assert breaker.state == "half_open"
    assert breaker.allow() is None  # the probe
    breaker.record_success()
    assert breaker.state == "closed"
    assert breaker.allow() is None
    breaker.record_failure()  # failure count starts again from zero
    assert breaker.state == "open"


def test_probe_failure_reopens_with_a_fresh_cooldown() -> None:
    clock = FakeClock()
    breaker = _breaker(clock, failure_threshold=2, cooldown_seconds=30.0)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(31)
    assert breaker.allow() is None
    breaker.record_failure()
    assert breaker.state == "open"
    assert breaker.allow() == pytest.approx(30.0)  # fresh cooldown, not the old one
    clock.advance(30)
    assert breaker.state == "half_open"


def test_half_open_probe_limit_and_release() -> None:
    clock = FakeClock()
    breaker = _breaker(clock, failure_threshold=1, cooldown_seconds=5.0)
    breaker.record_failure()
    clock.advance(5)
    assert breaker.allow() is None
    wait = breaker.allow()  # second concurrent probe is refused
    assert wait is not None and wait > 0
    breaker.release()
    assert breaker.allow() is None  # slot freed without changing state
    assert breaker.state == "half_open"


def test_half_open_max_admits_that_many_probes() -> None:
    clock = FakeClock()
    breaker = _breaker(
        clock, failure_threshold=1, cooldown_seconds=5.0, half_open_max=3
    )
    breaker.record_failure()
    clock.advance(5)
    assert [breaker.allow() for _ in range(3)] == [None, None, None]
    assert breaker.allow() is not None


def test_results_reported_while_open_are_ignored() -> None:
    clock = FakeClock()
    breaker = _breaker(clock, failure_threshold=1, cooldown_seconds=30.0)
    breaker.record_failure()
    clock.advance(10)
    breaker.record_failure()  # stale: must not extend the cooldown
    breaker.record_success()  # stale: must not close it
    assert breaker.state == "open"
    assert breaker.allow() == pytest.approx(20.0)


def test_threshold_zero_or_negative_never_opens() -> None:
    for threshold in (0, -1):
        breaker = _breaker(FakeClock(), failure_threshold=threshold)
        for _ in range(100):
            breaker.record_failure()
        assert breaker.state == "closed"
        assert breaker.allow() is None


def test_jitter_bounds_with_seeded_rng() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(1, 30.0, jitter=0.2, clock=clock, rng=random.Random(1234))
    seen: set[float] = set()
    for _ in range(200):
        breaker.record_failure()
        wait = breaker.allow()
        assert wait is not None
        assert 24.0 - 1e-9 <= wait <= 36.0 + 1e-9
        seen.add(round(wait, 6))
        clock.advance(wait)
        assert breaker.allow() is None  # half-open probe
        breaker.record_success()
    assert len(seen) > 100  # the cooldown really is spread out


def test_jitter_extremes_are_exact() -> None:
    for high, expected in ((False, 24.0), (True, 36.0)):
        breaker = CircuitBreaker(
            1, 30.0, jitter=0.2, clock=FakeClock(), rng=ExtremeRng(high)
        )
        breaker.record_failure()
        assert breaker.allow() == pytest.approx(expected)


def test_breaker_validation() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(cooldown_seconds=-1)
    with pytest.raises(ValueError):
        CircuitBreaker(jitter=1.0)
    with pytest.raises(ValueError):
        CircuitBreaker(jitter=-0.1)
    with pytest.raises(ValueError):
        CircuitBreaker(half_open_max=0)


def test_breaker_is_thread_safe() -> None:
    breaker = CircuitBreaker(800, 30.0, clock=FakeClock())

    def worker() -> None:
        for _ in range(100):
            breaker.record_failure()
            breaker.allow()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert breaker.state == "open"  # no failure was lost to a race: 8 * 100 == 800


# --- is_infrastructure_failure ---------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        "upstream_error: index store returned no object",
        "upstream_error",
        "upstream_error: cannot read a.txt: [Errno 5] Input/output error",
        "RuntimeError: boom",
        "TimeoutError: ",
        "ConnectionError: refused",
        "OSError: [Errno 104] Connection reset by peer",
        "requests.exceptions.ReadTimeout: HTTPSConnectionPool timed out",
        "deployment lookup failed: connection refused",
        "request timed out after 10s",
        "Timeout contacting railway",
        "the service is temporarily unavailable",
        "Connection reset by peer",
        "httpx.ConnectError: All connection attempts failed",
    ],
)
def test_infrastructure_failures(error: str) -> None:
    assert is_infrastructure_failure(error) is True


@pytest.mark.parametrize(
    "error",
    [
        None,
        "",
        "not_configured: RAILWAY_TOKEN missing",
        "invalid_name: bad service name",
        "policy forbids tool_x",
        "policy forbids writing a.txt",
        "approval required",
        "approval refused by operator",
        "forbidden: principal reader lacks the call scope",
        "rate_limited: tool call rate limit exceeded; retry in 3s",
        "circuit_open: tool tool_x is failing; retry in 20s",
        "unknown_field: undeclared argument 'x'",
        "bad_value: heartbeat.timeout must be > 0",
        "bad_type: SetRequest.prompt must be a string",
        "Unknown tool: nope",
        "TypeError: missing required arguments: name",
        "TypeError: unexpected arguments: extra",
        "ValueError: arguments must be a JSON object",
        "validation error: name is required",
        "interceptor_error: ToolRateLimitInterceptor failed",
        "something odd happened",
    ],
)
def test_caller_and_policy_failures_are_not_infrastructure(error: str | None) -> None:
    assert is_infrastructure_failure(error) is False


# --- ToolCircuitBreakerInterceptor ----------------------------------------------


def _call(name: str = "tool_x") -> ToolCall:
    return ToolCall(name, {}, None)


def _interceptor(
    clock: FakeClock, *, failure_threshold: int = 2, max_tools: int = 1024
) -> ToolCircuitBreakerInterceptor:
    return ToolCircuitBreakerInterceptor(
        failure_threshold=failure_threshold,
        cooldown_seconds=30.0,
        jitter=0.0,
        max_tools=max_tools,
        clock=clock,
        rng=random.Random(3),
    )


class Counter:
    """Dispatch stand-in returning a fixed payload and counting invocations."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        return self.payload


def _ok() -> Counter:
    return Counter(json.dumps({"result": 1}))


def _err(message: str) -> Counter:
    return Counter(json.dumps({"error": message}))


def _run(
    chain: list[ToolCallInterceptor], dispatch: Counter, name: str = "tool_x"
) -> ToolOutcome:
    return run_tool_call(chain, _call(name), dispatch)[1]


def test_opens_after_consecutive_infrastructure_failures() -> None:
    clock = FakeClock()
    breaker = _interceptor(clock)
    chain: list[ToolCallInterceptor] = [breaker]
    failing = _err("upstream_error: down")
    for _ in range(2):
        assert _run(chain, failing).status == "error"
    assert failing.calls == 2
    payload, outcome = run_tool_call(chain, _call(), failing)
    assert failing.calls == 2  # not dispatched
    assert outcome.status == "denied" and outcome.denial_code == "circuit_open"
    assert json.loads(payload)["error"].startswith("circuit_open:")
    denial = breaker.before(_call())
    assert isinstance(denial, ToolDenial)
    assert denial.code == "circuit_open"
    assert denial.retry_after == pytest.approx(30.0)
    # Our own denial neither counts nor extends the cooldown.
    clock.advance(10)
    again = breaker.before(_call())
    assert isinstance(again, ToolDenial)
    assert again.code == "circuit_open"
    assert again.message == "tool tool_x is failing; retry in 20s"
    assert again.retry_after == pytest.approx(20.0)


def test_half_open_probe_success_closes_and_failure_reopens() -> None:
    clock = FakeClock()
    breaker = _interceptor(clock, failure_threshold=1)
    chain: list[ToolCallInterceptor] = [breaker]
    _run(chain, _err("upstream_error: down"))
    clock.advance(30)
    failing = _err("upstream_error: still down")
    assert _run(chain, failing).status == "error"  # the probe is dispatched
    assert failing.calls == 1
    assert _run(chain, failing).denial_code == "circuit_open"
    assert failing.calls == 1
    clock.advance(30)
    healthy = _ok()
    assert _run(chain, healthy).status == "ok"
    inner = breaker.breaker("tool_x")
    assert inner is not None
    assert inner.state == "closed"
    assert _run(chain, healthy).status == "ok"
    assert healthy.calls == 2


def test_success_between_failures_resets_the_count() -> None:
    chain: list[ToolCallInterceptor] = [_interceptor(FakeClock(), failure_threshold=3)]
    for _ in range(5):
        _run(chain, _err("upstream_error: down"))
        _run(chain, _err("RuntimeError: boom"))
        assert _run(chain, _ok()).status == "ok"
    assert _run(chain, _ok()).status == "ok"


@pytest.mark.parametrize(
    "message",
    [
        "not_configured: RAILWAY_TOKEN missing",
        "invalid_name: bad",
        "policy forbids tool_x",
        "approval required",
        "bad_value: x must be > 0",
        "unknown_field: nope",
        "TypeError: missing required arguments: a",
    ],
)
def test_caller_errors_never_open_the_breaker(message: str) -> None:
    breaker = _interceptor(FakeClock(), failure_threshold=1)
    chain: list[ToolCallInterceptor] = [breaker]
    caller_error = _err(message)
    for _ in range(10):
        assert _run(chain, caller_error).status == "error"
    assert caller_error.calls == 10
    assert breaker.tracked_tools() == 0


def test_dispatch_exception_counts_as_infrastructure_failure() -> None:
    breaker = _interceptor(FakeClock(), failure_threshold=1)
    chain: list[ToolCallInterceptor] = [breaker]

    def explode() -> str:
        raise RuntimeError("socket closed")

    with pytest.raises(RuntimeError):
        run_tool_call(chain, _call(), explode)
    assert breaker.before(_call()) is not None


def test_probe_ending_in_caller_error_releases_slot_without_counting() -> None:
    clock = FakeClock()
    breaker = _interceptor(clock, failure_threshold=1)
    chain: list[ToolCallInterceptor] = [breaker]
    _run(chain, _err("upstream_error: down"))
    clock.advance(30)
    caller_error = _err("bad_value: x must be > 0")
    assert _run(chain, caller_error).status == "error"  # probe, caller's fault
    inner = breaker.breaker("tool_x")
    assert inner is not None and inner.state == "half_open"
    healthy = _ok()
    assert _run(chain, healthy).status == "ok"  # slot was released: next probe runs
    assert inner.state == "closed"


def test_probe_denied_by_a_later_interceptor_releases_slot() -> None:
    class Deny:
        def before(self, call: ToolCall) -> ToolDenial:
            del call
            return ToolDenial("forbidden", "nope")

        def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
            del call, outcome

    clock = FakeClock()
    breaker = _interceptor(clock, failure_threshold=1)
    _run([breaker], _err("upstream_error: down"))
    clock.advance(30)
    denied = _run([breaker, Deny()], _ok())
    assert denied.denial_code == "forbidden"
    inner = breaker.breaker("tool_x")
    assert inner is not None and inner.state == "half_open"
    assert _run([breaker], _ok()).status == "ok"  # the slot is free again
    assert inner.state == "closed"


def test_breakers_are_per_tool_and_lazily_created() -> None:
    breaker = _interceptor(FakeClock(), failure_threshold=1)
    chain: list[ToolCallInterceptor] = [breaker]
    for index in range(50):  # successes and unknown names allocate nothing
        _run(chain, _ok(), f"tool_{index}")
        _run(chain, _err("Unknown tool: nope"), f"ghost_{index}")
    assert breaker.tracked_tools() == 0
    _run(chain, _err("upstream_error: down"), "tool_a")
    assert _run(chain, _ok(), "tool_a").denial_code == "circuit_open"
    assert _run(chain, _ok(), "tool_b").status == "ok"
    assert breaker.tracked_tools() == 1


def test_breaker_map_is_bounded() -> None:
    breaker = _interceptor(FakeClock(), failure_threshold=1, max_tools=2)
    chain: list[ToolCallInterceptor] = [breaker]
    for name in ("a", "b", "c"):
        _run(chain, _err("upstream_error: down"), name)
    assert breaker.tracked_tools() == 2
    assert breaker.breaker("a") is None  # least recently used was evicted
    assert breaker.breaker("c") is not None


def test_interceptor_validation() -> None:
    with pytest.raises(ValueError):
        ToolCircuitBreakerInterceptor(jitter=2.0)
    with pytest.raises(ValueError):
        ToolCircuitBreakerInterceptor(max_tools=0)


def test_threshold_zero_interceptor_never_denies() -> None:
    breaker = _interceptor(FakeClock(), failure_threshold=0)
    chain: list[ToolCallInterceptor] = [breaker]
    failing = _err("upstream_error: down")
    for _ in range(20):
        assert _run(chain, failing).status == "error"
    assert failing.calls == 20
