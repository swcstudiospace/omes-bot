---
phase: 63-grokbot-enterprise-improvements
plan: "05"
subsystem: grokbot-observability
tags: [prometheus, traceparent, ndjson, redaction, access-log]
requires:
  - phase: 62
    provides: Audit redaction, interceptor chain, principal in scope state
provides:
  - Hand-written Prometheus text exposition with bounded label cardinality
  - Request and tool-call metrics, read-scoped `/metrics`
  - W3C trace context and a forge-proof request id on every response
  - NDJSON logging with redaction and an access log with no query string or headers
affects: [63-08, 63-06]
tech-stack:
  added: []
  patterns: [pure ASGI middleware, contextvar request id, per-metric child cap]
key-files:
  created:
    - omega_prime/grokbot/metrics.py
    - omega_prime/grokbot/telemetry.py
    - omega_prime/tests/test_grokbot_metrics.py
    - omega_prime/tests/test_grokbot_telemetry.py
key-decisions:
  - "Request ids are minted by the host; an inbound `X-Request-Id` is ignored so ids cannot be forged into logs or the audit trail. A malformed inbound `traceparent` is replaced, never echoed."
  - "Metric labels are bounded: tool names only when they are served tools (else `unknown`); paths are grouped; label sets beyond a per-metric cap fold into one `overflow` child."
  - "Observers must precede denying interceptors: `run_tool_call` runs `after` only for interceptors whose `before` ran, so a metrics interceptor placed after a denier never counts the denial."
  - "`configure_logging` sets `propagate=False` on the `omega_prime` logger so a host that configures the root logger does not print every record twice."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-05 Observability

Commit `7b70132`. Requirement: GRI-05.

Metrics: `omega_http_requests_total`, `omega_http_request_duration_seconds`, `omega_http_in_flight`,
`omega_tool_calls_total`, `omega_tool_call_duration_seconds`, `omega_tool_calls_in_flight`,
`omega_tool_denials_total{code}`, `omega_auth_failures_total{reason}`, `omega_build_info`. Streaming (SSE)
responses are observed at response start so endless streams still count. The access log sanitizes control
characters and truncates the path so a crafted request cannot inject fake log lines. 68 tests.
