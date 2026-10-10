---
phase: 63-grokbot-enterprise-improvements
plan: "08"
subsystem: grokbot-integration
tags: [integration, middleware-order, interceptor-order, cli, structured-logs]
requires:
  - phase: 63
    provides: Streamable HTTP, scoped tokens, approvals, traffic protection, observability (63-01..05)
provides:
  - One host composing every improvement, with real-socket integration tests
  - CLI flags for every new protection; the Dockerfile CMD is accepted by the parser
  - `--log-format json` covers every process log line
affects: [63-06, 63-07, v11-closeout]
tech-stack:
  added: []
  patterns: [observers before denying interceptors, request context outermost, one shared tool gate]
key-files:
  modified:
    - omega_prime/grokbot/remote.py
    - omega_prime/grokbot/manifest.py
    - omega_prime/grokbot/oneclick.py
    - omega_prime/mcp_server.py
    - omega_prime/tests/conftest.py
  created:
    - omega_prime/tests/test_grokbot_integration.py
key-decisions:
  - "Interceptor order is InFlight, Audit, Metrics, Scope, ToolRateLimit, CircuitBreaker: `run_tool_call` stops at the first denial and runs `after` only for interceptors whose `before` ran, so an observer placed after a denier never records the denial. The earlier order silently dropped scope denials from the audit log."
  - "Default limits are generous (600 requests/min and 300 tool calls/min per principal): they exist to stop runaway clients, not to ration a coding agent that fires several quick tool calls per second."
  - "A principal presenting another's `Mcp-Session-Id` gets 404, hiding that the session exists."
  - "`/readyz` fails (503) when the token store file is unreadable, even though authentication keeps denying everyone."
  - "uvicorn's own access log is off in the integrated host; `AccessLogMiddleware` replaces it and never logs a query string."
  - "A test-suite guard (`conftest.py`) snapshots and restores the process-global loggers around every test: `configure_logging` sets `propagate=False`, which makes pytest attach its own capture handlers and broke later logging assertions depending on test order."
duration: 2 units
completed: 2026-10-09
---

# Summary: 63-08 Integration wiring

Commits `08023ea`, `9bddee6`, `fc08354`, `48f766b`. Requirements: GRI-01..GRI-05.

## Verified on a real process

With reader, caller and admin tokens: request ids and `traceparent` on responses; `/manifest.json` lists 108
tools matching `/healthz`; `/metrics` is 401 without a token and exposes HTTP series with one; `/mcp` and `/sse`
both list 108 tools and call one; a read-only token's call is `forbidden`, audited as `denied`, and counted as
`omega_tool_denials_total{code="forbidden"} 1`; a call-scope token gets 403 on `/admin/approvals` while an admin
gets 201 with `expires_at`; a revoked token is 401 on the next request with no restart; the token appears in
neither the log nor the audit file.

## Deviations

`CompositeTokenStore` takes no clock (the injected clock goes to `FileTokenStore` and the limiters, throttle,
breaker and approval log); the file store is first in the composite; `serve_sse` drops closed `omega_prime` log
handlers before `configure_logging` so a closed stderr cannot turn into exit code 2.
