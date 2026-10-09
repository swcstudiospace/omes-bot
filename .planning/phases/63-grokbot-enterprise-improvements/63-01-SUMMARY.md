---
phase: 63-grokbot-enterprise-improvements
plan: "01"
subsystem: grokbot-transport
tags: [mcp, streamable-http, sessions, principal-binding]
requires:
  - phase: 62
    provides: Principal-carrying auth middleware and the shared ToolGate
provides:
  - MCP Streamable HTTP at `/mcp` next to legacy SSE
  - Sessions bound to the principal that opened them
affects: [63-08, 63-06]
tech-stack:
  added: []
  patterns: [raw ASGI endpoint, SDK session-owner mechanism fed from our principal]
key-files:
  created:
    - omega_prime/grokbot/streamable.py
    - omega_prime/tests/test_grokbot_streamable.py
key-decisions:
  - "A principal presenting someone else's `Mcp-Session-Id` gets 404, exactly as for an unknown session: it never learns the session exists. (The context doc said 403; the SDK's 404 is the better behavior.)"
  - "The SDK enforces the body limit (413), the session cap (503) and idle expiry (404); nothing is reimplemented."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-01 Streamable HTTP transport

Commit `8beab0e`. Requirement: GRI-01.

`build_streamable_http(server, ...)` wraps the SDK `StreamableHTTPSessionManager` (stateful sessions). The
route is a raw ASGI object so `/mcp` never redirects. Before delegating, the endpoint copies the caller's
`Principal` into `scope["user"]` (placeholder token `principal:<id>`, never the bearer token) so the SDK's own
session-owner check applies. 13 real-socket tests cover initialize/list/call, cross-principal 404, 413, 503,
DELETE and 405. One test reads the SDK's private `_session_owners`, so an SDK upgrade may need it updated.
