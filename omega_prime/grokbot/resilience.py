# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Resilience: a per-tool circuit breaker so a failing upstream is not hammered.

`CircuitBreaker` is a small thread-safe state machine (closed -> open -> half_open
-> closed/open) with a jittered cooldown and an injectable clock and RNG.
`ToolCircuitBreakerInterceptor` keeps one breaker per tool name and counts only
infrastructure failures (`is_infrastructure_failure`), so caller mistakes such as
bad arguments, policy or approval refusals and rate limits never open a breaker.

Bounded memory: the interceptor creates a breaker only when a tool records its first
infrastructure failure (an absent breaker is equivalent to a closed one with no
failures), so arbitrary caller-supplied tool names cannot allocate anything, and it
holds at most `MAX_TRACKED_TOOLS` breakers (least recently used evicted).
"""

from __future__ import annotations

import random
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable

from omega_prime.grokbot.interceptors import ToolCall, ToolDenial, ToolOutcome

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"

MAX_TRACKED_TOOLS = 1024
_PROBE_RETRY_SECONDS = 1.0
_CIRCUIT_OPEN = "circuit_open"


class CircuitBreaker:
    """closed / open / half_open breaker with a jittered cooldown.

    `failure_threshold` consecutive failures open it for
    `cooldown_seconds * (1 +- jitter)`. Once the cooldown has elapsed the next
    `allow()` admits up to `half_open_max` concurrent probes; a probe success closes
    the breaker, a probe failure re-opens it with a fresh jittered cooldown.
    `failure_threshold <= 0` means the breaker never opens. Thread-safe.

    A success or failure reported while open is ignored: it belongs to a call that
    was admitted before the breaker opened.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        *,
        jitter: float = 0.2,
        half_open_max: int = 1,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        if not 0.0 <= jitter < 1.0:
            raise ValueError("jitter must be in [0, 1)")
        if half_open_max < 1:
            raise ValueError("half_open_max must be >= 1")
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._jitter = jitter
        self._half_open_max = half_open_max
        self._clock = clock
        self._rng = rng if rng is not None else random.Random()
        self._lock = threading.Lock()
        self._state = STATE_CLOSED
        self._failures = 0
        self._probes = 0
        self._open_until = 0.0

    @property
    def state(self) -> str:
        with self._lock:
            self._advance(self._clock())
            return self._state

    def allow(self) -> float | None:
        """None to proceed, else the seconds until the next probe may be admitted."""
        with self._lock:
            now = self._clock()
            self._advance(now)
            if self._state == STATE_CLOSED:
                return None
            if self._state == STATE_OPEN:
                return self._open_until - now
            if self._probes < self._half_open_max:
                self._probes += 1
                return None
            return _PROBE_RETRY_SECONDS

    def record_success(self) -> None:
        with self._lock:
            self._advance(self._clock())
            if self._state == STATE_CLOSED:
                self._failures = 0
            elif self._state == STATE_HALF_OPEN:
                self._close()

    def record_failure(self) -> None:
        with self._lock:
            now = self._clock()
            self._advance(now)
            if self._state == STATE_HALF_OPEN:
                self._open(now)
            elif self._state == STATE_CLOSED and self._threshold > 0:
                self._failures += 1
                if self._failures >= self._threshold:
                    self._open(now)

    def release(self) -> None:
        """Free a half-open probe slot for a call that proved nothing either way."""
        with self._lock:
            self._advance(self._clock())
            if self._state == STATE_HALF_OPEN and self._probes > 0:
                self._probes -= 1

    def _advance(self, now: float) -> None:
        if self._state == STATE_OPEN and now >= self._open_until:
            self._state = STATE_HALF_OPEN
            self._probes = 0

    def _open(self, now: float) -> None:
        spread = self._rng.uniform(-self._jitter, self._jitter)
        self._state = STATE_OPEN
        self._open_until = now + self._cooldown * (1.0 + spread)
        self._failures = 0
        self._probes = 0

    def _close(self) -> None:
        self._state = STATE_CLOSED
        self._failures = 0
        self._probes = 0


# Denials and refusals that are the caller's doing, never the upstream's.
_CALLER_PREFIXES = (
    "not_configured:",
    "invalid_name:",
    "policy forbids",
    "approval",
    "forbidden",
    "rate_limited",
    _CIRCUIT_OPEN,
    "interceptor_error",
    "unknown_",
    "bad_",
    "unknown tool",
    "validation",
)
_CALLER_FRAGMENTS = (
    "policy forbids",
    "approval required",
    "not approved",
    "validation error",
    "missing required arguments",
    "unexpected arguments",
    "arguments must be",
)
_TRANSIENT_FRAGMENTS = (
    "timed out",
    "timeout",
    "connection refused",
    "connection reset",
    "temporarily unavailable",
)
_UPSTREAM_PREFIX = "upstream_error"
# `ToolRegistry.dispatch` reports a handler exception as "<ExceptionType>: <message>".
_HANDLER_EXCEPTION = re.compile(r"^(?:[A-Za-z_]\w*\.)*[A-Z]\w*(?:Error|Exception)\b:")


def is_infrastructure_failure(error: str | None) -> bool:
    """True only for transient/upstream failures worth counting against a tool.

    True: the `upstream_error` prefix (`upstream_error: ...`), a handler exception as
    the registry reports it (`RuntimeError: boom`), and messages mentioning a
    timeout, a refused or reset connection, or a temporarily unavailable service.
    False: everything the caller or policy caused (`not_configured:`,
    `invalid_name:`, `policy forbids`, approval refusals, `forbidden`,
    `rate_limited`, `circuit_open`, `unknown_field`, `bad_value`, argument and
    validation errors) and anything unrecognised.
    """
    if not error:
        return False
    text = error.strip().lower()
    if text.startswith(_CALLER_PREFIXES):
        return False
    if text == _UPSTREAM_PREFIX or text.startswith(f"{_UPSTREAM_PREFIX}:"):
        return True
    if any(fragment in text for fragment in _CALLER_FRAGMENTS):
        return False
    if any(fragment in text for fragment in _TRANSIENT_FRAGMENTS):
        return True
    return _HANDLER_EXCEPTION.match(error.strip()) is not None


def _is_infrastructure_outcome(outcome: ToolOutcome) -> bool:
    return outcome.is_error and is_infrastructure_failure(outcome.error)


class ToolCircuitBreakerInterceptor:
    """One `CircuitBreaker` per tool name; denial code `circuit_open`.

    `after` records a success for an ok result and a failure only when the result
    is an error AND `is_infrastructure_failure(outcome.error)`. Caller errors and
    denials never count; a half-open probe that ends that way releases its slot.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        jitter: float = 0.2,
        half_open_max: int = 1,
        max_tools: int = MAX_TRACKED_TOOLS,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        # Fail on bad settings now rather than on the first tool failure.
        CircuitBreaker(
            failure_threshold,
            cooldown_seconds,
            jitter=jitter,
            half_open_max=half_open_max,
        )
        if max_tools < 1:
            raise ValueError("max_tools must be >= 1")
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._jitter = jitter
        self._half_open_max = half_open_max
        self._max_tools = max_tools
        self._clock = clock
        self._rng = rng
        self._lock = threading.Lock()
        self._breakers: OrderedDict[str, CircuitBreaker] = OrderedDict()

    def breaker(self, name: str) -> CircuitBreaker | None:
        """The breaker for a tool that has failed before, else None."""
        with self._lock:
            return self._breakers.get(name)

    def tracked_tools(self) -> int:
        with self._lock:
            return len(self._breakers)

    def before(self, call: ToolCall) -> ToolDenial | None:
        breaker = self._lookup(call.name)
        if breaker is None:
            return None
        wait = breaker.allow()
        if wait is None:
            return None
        return ToolDenial(
            _CIRCUIT_OPEN,
            f"tool {call.name} is failing; retry in {max(1, round(wait))}s",
            wait,
        )

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        if outcome.status == "ok":
            breaker = self._lookup(call.name)
            if breaker is not None:
                breaker.record_success()
            return
        if outcome.status == "denied" and outcome.denial_code == _CIRCUIT_OPEN:
            return  # our own denial admitted nothing
        if outcome.status != "denied" and _is_infrastructure_outcome(outcome):
            self._get_or_create(call.name).record_failure()
            return
        # A caller error, or a denial by a later interceptor after we admitted
        # the call: free a half-open probe slot without counting either way.
        breaker = self._lookup(call.name)
        if breaker is not None:
            breaker.release()

    def _lookup(self, name: str) -> CircuitBreaker | None:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is not None:
                self._breakers.move_to_end(name)
            return breaker

    def _get_or_create(self, name: str) -> CircuitBreaker:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is None:
                breaker = CircuitBreaker(
                    self._failure_threshold,
                    self._cooldown,
                    jitter=self._jitter,
                    half_open_max=self._half_open_max,
                    clock=self._clock,
                    rng=self._rng,
                )
                self._breakers[name] = breaker
                while len(self._breakers) > self._max_tools:
                    self._breakers.popitem(last=False)
            else:
                self._breakers.move_to_end(name)
            return breaker


__all__ = [
    "MAX_TRACKED_TOOLS",
    "STATE_CLOSED",
    "STATE_HALF_OPEN",
    "STATE_OPEN",
    "CircuitBreaker",
    "ToolCircuitBreakerInterceptor",
    "is_infrastructure_failure",
]
