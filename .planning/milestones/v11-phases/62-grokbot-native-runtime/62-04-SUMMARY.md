---
phase: 62-grokbot-native-runtime
plan: "04"
subsystem: grokbot-lifecycle
tags: [supervisor, restart, health-probe, process-group]
requires:
  - phase: 62
    provides: Atomic state writer (`_io`)
provides:
  - Supervisor whose `--stop` stops the supervisor and its child
  - Health probing, capped jittered backoff, restart budget reset after stable uptime
  - Non-zero exit when the supervisor gives up; atomic state file
affects: [62-06, 63-07]
tech-stack:
  added: []
  patterns: [child in its own process group, injectable clock/sleep/rng]
key-files:
  modified:
    - omega_prime/grokbot/supervisor.py
    - omega_prime/tests/test_grokbot_supervisor.py
key-decisions:
  - "The child runs in its own session so a terminal Ctrl-C reaches only the supervisor, which stops the child group with SIGTERM then SIGKILL."
  - "`--stop` signals the supervisor pid from the state file (signalling the child made the supervisor restart it)."
  - "The default supervised command is the SSE server: the stdio server exits without a client and caused a restart loop."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 62-04 Supervisor and lifecycle fixes

Commit `1d444c0` (rebased: `4e5f262`). Requirement: GRK-08 (supervisor half).

## What shipped

`run_loop()` returns 0 after a requested stop and 1 after exceeding `max_restarts` (with `last_error`).
State carries `supervisor_pid`, `child_pid`, `healthy`, `restarts`, `last_exit_code`, `last_error`, and is
written atomically at every transition. A hung child (N consecutive failed `GET /healthz`) is killed and
restarted. A child that ran at least `stable_after_sec` resets the restart counter, so a flaky but long-lived
server is not treated as a crash loop.

## Deviations

A child that shares the supervisor's process group is signalled individually (so the group kill never hits
the test runner); the final state write clears `supervisor_pid` so a later `--stop` cannot signal a reused
pid; `_pid_alive` treats a zombie as dead.
