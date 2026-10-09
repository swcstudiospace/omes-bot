---
phase: 63-grokbot-enterprise-improvements
plan: "04"
subsystem: grokbot-resilience
tags: [rate-limit, throttle, circuit-breaker, bounded-memory]
requires:
  - phase: 62
    provides: Interceptor chain, scope hierarchy
provides:
  - Two-tier token-bucket rate limiter (per principal and global) with middleware and a tool interceptor
  - Auth-failure throttle that runs before authentication
  - Per-tool circuit breaker with jittered half-open recovery
affects: [63-08]
tech-stack:
  added: []
  patterns: [LRU-capped state, injectable clock, caller-vs-infrastructure failure taxonomy]
key-files:
  created:
    - omega_prime/grokbot/ratelimit.py
    - omega_prime/grokbot/resilience.py
    - omega_prime/tests/test_grokbot_ratelimit.py
    - omega_prime/tests/test_grokbot_resilience.py
key-decisions:
  - "Only infrastructure failures open a breaker (`upstream_error`, timeouts, connection errors, handler exceptions); policy, approval, validation, `not_configured`, `rate_limited` and `circuit_open` never do, so a caller's mistakes cannot take a tool offline for everyone."
  - "A breaker is created on a tool's first infrastructure failure, so caller-supplied tool names allocate nothing; the map is LRU-capped."
  - "A half-open probe that ends in a caller error, or is denied by a later interceptor, releases its slot without counting."
  - "429 bodies are `{error: rate_limited | too_many_auth_failures, retry_after}` with a whole-second `Retry-After`."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-04 Traffic protection

Commit `913e639`. Requirement: GRI-04.

Every structure is bounded (10,000 rate-limit keys, 1,024 breakers, bounded failure windows) and thread-safe,
because tool calls run in worker threads. Defaults are set in 63-08: 600 requests/min and 300 tool calls/min per
principal (a coding agent legitimately fires several quick calls per second, so the limits stop runaway clients,
not normal ones), 10 auth failures per 60 s per client, breaker at 5 failures with a 30 s cooldown; 0 disables
each. 89 tests with fake clocks and seeded rng; no real sleeps.
