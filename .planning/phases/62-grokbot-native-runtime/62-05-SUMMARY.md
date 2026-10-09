---
phase: 62-grokbot-native-runtime
plan: "05"
subsystem: grokbot-remote
tags: [sse, transport-security, health, graceful-shutdown, e2e]
requires:
  - phase: 62
    provides: Security core, interceptors, audit chain, `load_runtime`, `ToolGate`
provides:
  - Fail-closed remote SSE host with SDK Host/Origin validation and body limit
  - Truthful `/healthz` and `/readyz`; graceful drain on SIGTERM
  - Every tool call and auth failure audited without token text
  - `mcp_server` CLI flags and `--approve` on both transports
  - Real-socket end-to-end tests driven by the MCP SDK client
affects: [62-06, 63-01, 63-08, 63-07]
tech-stack:
  added: []
  patterns: [raw ASGI SSE endpoint, drain-then-exit uvicorn subclass, access-log query stripping]
key-files:
  modified:
    - omega_prime/grokbot/remote.py
    - omega_prime/mcp_server.py
    - omega_prime/tests/test_grokbot_remote.py
  created:
    - omega_prime/tests/test_grokbot_e2e.py
    - omega_prime/tests/test_grokbot_cli.py
key-decisions:
  - "`/sse` is a raw ASGI endpoint: when the SDK rejects a request on Host/Origin it has already responded, and a function endpoint would send a second response."
  - "`_OriginGuard` covers a non-loopback bind with bearer auth and no public host, where the SDK would switch Host and Origin validation off together."
  - "`GracefulServer` bypasses uvicorn's `handle_exit` so SSE streams are not cut before in-flight results are delivered; it returns 0 after a clean drain."
  - "uvicorn's access log is filtered to drop query strings (found by a live run: a client that put its token in the URL leaked it into the log)."
duration: 2 units
completed: 2026-10-09
---

# Summary: 62-05 Remote host, CLI flags, real-transport tests

Commits `b6392ad` (rebased: `9e4d0c3`). Requirements: GRK-01..GRK-04, GRK-08, GRK-10.

## What shipped

`create_sse_app` fails closed before serving (no token on a non-loopback bind, invalid roster/policy/approval,
malformed public URL or host/origin entries). `serve_sse` returns 2 with `omega-prime-mcp-server: <reason>`.
Middleware order is CORS (named origins only, never `*`) then pure-ASGI auth then the Origin guard.
`/readyz` is 503 while draining or when the audit log is not writable; `/healthz` reports the version and
the number of tools actually served.

## Verified on a real process (not only in-process tests)

401 with `WWW-Authenticate` without a token; 401 for `?token=<valid>`; 403 for a hostile Origin; an
authenticated `/sse` opens an event stream; SIGTERM with an SSE client attached exits 0 in about 0.1 to
1.3 s with `/readyz` answering 503 while draining; the token appears 0 times in server output or the audit
log after the access-log fix. A non-loopback bind with no token exits 2 with a one-line reason.

## Deviations

`/readyz` check names (`registry`, `roster`, `policy`, `audit`, `shutdown`) were chosen by the unit; the
first signal does not re-raise after a clean drain.
