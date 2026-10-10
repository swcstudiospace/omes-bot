---
phase: 62-grokbot-native-runtime
plan: "01"
subsystem: grokbot-security
tags: [auth, bearer, scopes, interceptors, fail-closed, worker-thread]
requires:
  - phase: 61
    provides: Typed tool registry, approval log and seat policy the host serves
provides:
  - Constant-time scoped bearer tokens and pure-ASGI header-only auth
  - Bind-safety check that refuses an unauthenticated non-loopback listener
  - Tool-call interceptors (scope, audit, in-flight) with fail-closed semantics
  - Fail-closed `load_runtime` shared by both transports
  - `ToolGate`: tool calls run in a worker thread, one at a time by default
affects: [62-03, 62-05, 62-06, 63-01, 63-02, 63-03, 63-04, 63-05]
tech-stack:
  added: []
  patterns: [pure ASGI middleware, interceptor chain, fail-closed loader, serial worker-thread gate]
key-files:
  created:
    - omega_prime/grokbot/security.py
    - omega_prime/grokbot/interceptors.py
    - omega_prime/grokbot/_io.py
    - omega_prime/tests/test_grokbot_security.py
    - omega_prime/tests/test_grokbot_interceptors.py
    - omega_prime/tests/test_grokbot_runtime.py
    - omega_prime/tests/test_grokbot_io.py
  modified:
    - omega_prime/mcp_server.py
key-decisions:
  - "A token in a query string is never a credential (D-02); the Authorization header is the only source."
  - "A raising interceptor `before` is a denial (`interceptor_error`), never a pass."
  - "`load_runtime` rejects an empty roster, not only a missing one: serving nothing silently fails open on intent."
  - "Tool dispatch moved off the event loop (`ToolGate`): found during review, not in the original plan."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 62-01 Bearer security core, interceptors, runtime loader

Commit `1d444c0` (rebased: `4e5f262`). Requirements: GRK-01, GRK-02, GRK-05.

## What shipped

- `TokenStore` hashes the presented token once and compares it against every stored digest with
  `hmac.compare_digest` (no early exit). `AuthMiddleware` is pure ASGI (no `BaseHTTPMiddleware`, which
  breaks SSE), answers 401 with `WWW-Authenticate: Bearer`, and hands a `Principal` to the app.
- `check_bind_safety` refuses `0.0.0.0` without a token unless `--allow-insecure-no-auth` is explicit.
- `ScopeInterceptor`, `AuditInterceptor` (argument key names and a SHA-256 digest, never values) and
  `InFlightInterceptor` wrap every `tools/call`.
- `load_runtime` raises `RuntimeConfigError` for a missing/empty roster, an invalid seat policy or a
  refused approval; both transports use it.

## Found in review (post-wave)

`call_tool_handler` ran the synchronous `registry.dispatch` on the event loop. One slow tool froze
`/healthz`, SSE keepalives and shutdown, made `in_flight` unobservable, and broke tools that call
`asyncio.run` (`RuntimeError: asyncio.run() cannot be called from a running event loop`). `ToolGate`
(anyio `CapacityLimiter`, default one at a time because tools share files and state without locks) fixes
all three. A mutation check with the old inline dispatch fails 3 of the 4 new regression tests.

## Deviations

`TokenStore` validates digests and scopes at construction; `AuditInterceptor` validates `args_mode`;
the bad-approval message names the `(tool, approver)` pair. The full suite also caught a static guard
(`test_lint_types.py` pins the literal `is_error=is_error`), which the code now honours.
