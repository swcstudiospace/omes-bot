# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Traffic protection: request/tool rate limits and an auth-failure throttle.

Everything here is thread-safe (tool interceptors run in a worker thread while the
middleware runs on the event loop), takes an injectable monotonic clock, and holds
no event-loop-bound state.

Bounded memory: `RateLimiter` keeps at most `MAX_TRACKED_KEYS` per-key buckets and
`AuthFailureThrottle` at most `MAX_TRACKED_CLIENTS` clients (each holding at most
`max_failures` timestamps); both evict the least recently used entry. An evicted key
simply starts again with a full bucket / no failures, so rotating identities can
never grow memory, only slightly weaken the limit for the evicted entry.

Only principal ids and client hosts are used as keys or reported in events; headers,
tokens and query strings are never read.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable
from typing import Any

from starlette.responses import JSONResponse

from omega_prime.grokbot.interceptors import ToolCall, ToolDenial, ToolOutcome
from omega_prime.grokbot.security import principal_from_scope

logger = logging.getLogger(__name__)

MAX_TRACKED_KEYS = 10_000
MAX_TRACKED_CLIENTS = 10_000
DEFAULT_EXEMPT_PATHS = ("/healthz", "/readyz")
_SECONDS_PER_MINUTE = 60.0
_UNKNOWN_CLIENT = "unknown"
_LOCAL_CALLER = "local"
_ROUND_DIGITS = 6


def _retry_after_seconds(wait: float) -> int:
    """Whole seconds for a `Retry-After` header: ceil, never below 1."""
    return max(1, math.ceil(round(wait, _ROUND_DIGITS)))


class _Bucket:
    """A token bucket; callers serialize access with the limiter lock."""

    __slots__ = ("capacity", "last", "rate", "tokens")

    def __init__(self, capacity: float, rate: float, now: float) -> None:
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity
        self.last = now

    def refill(self, now: float) -> None:
        elapsed = now - self.last
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last = now

    def wait_for_token(self) -> float:
        """Seconds until one whole token is available (0.0 when one is)."""
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.rate


class RateLimiter:
    """A token bucket per key plus one optional global bucket.

    Each bucket refills at `limit / 60` tokens per second. A key bucket holds
    `burst or per_key_per_minute` tokens, the global bucket `global_per_minute`.
    `acquire` consumes one token from every enabled tier only when all of them
    can pay, so a denial by one tier never spends the other. A tier whose limit is
    0 is disabled; with both disabled `acquire` always allows.

    Memory is bounded: at most `MAX_TRACKED_KEYS` key buckets (LRU).
    """

    def __init__(
        self,
        per_key_per_minute: int,
        global_per_minute: int = 0,
        *,
        burst: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if per_key_per_minute < 0 or global_per_minute < 0:
            raise ValueError("rate limits must be >= 0")
        if burst is not None and burst < 1:
            raise ValueError("burst must be >= 1")
        self._per_key = per_key_per_minute
        self._global_limit = global_per_minute
        self._burst = burst if burst is not None else per_key_per_minute
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._global: _Bucket | None = None
        if global_per_minute > 0:
            self._global = _Bucket(
                float(global_per_minute),
                global_per_minute / _SECONDS_PER_MINUTE,
                clock(),
            )

    @property
    def enabled(self) -> bool:
        return self._per_key > 0 or self._global_limit > 0

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._buckets)

    def acquire(self, key: str) -> float | None:
        """None when allowed, else the seconds until a request would be allowed."""
        if not self.enabled:
            return None
        with self._lock:
            now = self._clock()
            key_bucket = self._key_bucket(key, now)
            if self._global is not None:
                self._global.refill(now)
            waits = [
                bucket.wait_for_token()
                for bucket in (key_bucket, self._global)
                if bucket is not None
            ]
            wait = max(waits)
            if wait > 0.0:
                return wait
            for bucket in (key_bucket, self._global):
                if bucket is not None:
                    bucket.tokens -= 1.0
            return None

    def _key_bucket(self, key: str, now: float) -> _Bucket | None:
        if self._per_key <= 0:
            return None
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(
                float(self._burst), self._per_key / _SECONDS_PER_MINUTE, now
            )
            self._buckets[key] = bucket
            while len(self._buckets) > MAX_TRACKED_KEYS:
                self._buckets.popitem(last=False)
        else:
            self._buckets.move_to_end(key)
            bucket.refill(now)
        return bucket


def _client_host(scope: Any) -> str:
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return _UNKNOWN_CLIENT


async def _reject(
    scope: Any, receive: Any, send: Any, body: dict[str, Any], wait: float
) -> None:
    seconds = _retry_after_seconds(wait)
    response = JSONResponse(
        {**body, "retry_after": seconds},
        status_code=429,
        headers={"Retry-After": str(seconds), "Cache-Control": "no-store"},
    )
    await response(scope, receive, send)


class RateLimitMiddleware:
    """Pure ASGI request rate limit; place it AFTER authentication.

    The key is the authenticated principal's id, else the client host. Exempt
    paths (matched exactly) are never limited. A denial is `429` with
    `{"error": "rate_limited", "retry_after": n}` and a `Retry-After` header.
    `on_limited` receives `{"key", "path", "retry_after"}`; its exceptions are
    swallowed.
    """

    def __init__(
        self,
        app: Any,
        *,
        limiter: RateLimiter,
        exempt_paths: Iterable[str] = DEFAULT_EXEMPT_PATHS,
        on_limited: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.exempt_paths = frozenset(exempt_paths)
        self.on_limited = on_limited

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("path", "") in self.exempt_paths:
            await self.app(scope, receive, send)
            return
        principal = principal_from_scope(scope)
        key = principal.id if principal is not None else _client_host(scope)
        wait = self.limiter.acquire(key)
        if wait is None:
            await self.app(scope, receive, send)
            return
        self._report(key, scope.get("path", ""), wait)
        await _reject(scope, receive, send, {"error": "rate_limited"}, wait)

    def _report(self, key: str, path: str, wait: float) -> None:
        if self.on_limited is None:
            return
        try:
            self.on_limited({"key": key, "path": path, "retry_after": wait})
        except Exception as exc:
            logger.warning("rate limit callback raised %s", type(exc).__name__)


class AuthFailureThrottle:
    """Per-client sliding window of authentication failures.

    `record(client)` notes one failure; `blocked(client)` returns the seconds until
    the oldest counted failure leaves the window once `max_failures` failures are
    inside it, else None. `max_failures=0` disables the throttle.

    Memory is bounded: at most `MAX_TRACKED_CLIENTS` clients (LRU), each holding at
    most `max_failures` timestamps.
    """

    def __init__(
        self,
        max_failures: int,
        window_seconds: float = 60.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_failures < 0:
            raise ValueError("max_failures must be >= 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: OrderedDict[str, deque[float]] = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self._max > 0

    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._failures)

    def record(self, client: str) -> None:
        if self._max <= 0:
            return
        with self._lock:
            now = self._clock()
            window = self._failures.get(client)
            if window is None:
                window = deque(maxlen=self._max)
                self._failures[client] = window
                while len(self._failures) > MAX_TRACKED_CLIENTS:
                    self._failures.popitem(last=False)
            else:
                self._failures.move_to_end(client)
            self._expire(window, now)
            window.append(now)

    def blocked(self, client: str) -> float | None:
        if self._max <= 0:
            return None
        with self._lock:
            window = self._failures.get(client)
            if window is None:
                return None
            now = self._clock()
            self._expire(window, now)
            if not window:
                del self._failures[client]
                return None
            if len(window) < self._max:
                return None
            return window[0] + self._window - now

    def _expire(self, window: deque[float], now: float) -> None:
        horizon = now - self._window
        while window and window[0] <= horizon:
            window.popleft()


class AuthThrottleMiddleware:
    """Pure ASGI guard placed BEFORE authentication.

    Answers `429` with `Retry-After` while `throttle.blocked(client)`. A blocked
    request never reaches the auth layer, so it does not extend its own lockout.
    The integrator feeds failures in with `throttle.record` from the auth
    `on_failure` hook.
    """

    def __init__(
        self,
        app: Any,
        *,
        throttle: AuthFailureThrottle,
        exempt_paths: Iterable[str] = DEFAULT_EXEMPT_PATHS,
    ) -> None:
        self.app = app
        self.throttle = throttle
        self.exempt_paths = frozenset(exempt_paths)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("path", "") in self.exempt_paths:
            await self.app(scope, receive, send)
            return
        wait = self.throttle.blocked(_client_host(scope))
        if wait is None:
            await self.app(scope, receive, send)
            return
        await _reject(scope, receive, send, {"error": "too_many_auth_failures"}, wait)


class ToolRateLimitInterceptor:
    """Rate-limit `tools/call` per principal id (`local` without a principal)."""

    def __init__(self, limiter: RateLimiter) -> None:
        self._limiter = limiter

    def before(self, call: ToolCall) -> ToolDenial | None:
        principal = call.principal
        key = principal.id if principal is not None else _LOCAL_CALLER
        wait = self._limiter.acquire(key)
        if wait is None:
            return None
        return ToolDenial(
            "rate_limited",
            f"tool call rate limit exceeded; retry in {_retry_after_seconds(wait)}s",
            wait,
        )

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call, outcome


__all__ = [
    "DEFAULT_EXEMPT_PATHS",
    "MAX_TRACKED_CLIENTS",
    "MAX_TRACKED_KEYS",
    "AuthFailureThrottle",
    "AuthThrottleMiddleware",
    "RateLimitMiddleware",
    "RateLimiter",
    "ToolRateLimitInterceptor",
]
