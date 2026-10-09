---
phase: 62-grokbot-native-runtime
plan: "06"
subsystem: grokbot-launcher
tags: [oneclick, doctor, emulator, preflight, strict]
requires:
  - phase: 62
    provides: Manifest/lint (62-03), remote host and CLI (62-05), runtime loader (62-01)
provides:
  - Strict 1-click launcher (preflight exit 3, bind safety exit 2, `--generate-token`)
  - Doctor with 15 checks including policy, roster, template, audit chain, bind exposure
  - Emulator that drives the same runtime as the server
affects: [63-06, 63-07]
tech-stack:
  added: []
  patterns: [strict-by-default preflight, names-only secret reporting, production-runtime emulation]
key-files:
  modified:
    - omega_prime/grokbot/oneclick.py
    - omega_prime/grokbot/doctor.py
    - omega_prime/grokbot/emulator.py
    - omega_prime/tests/test_grokbot_oneclick.py
    - omega_prime/tests/test_grokbot_doctor.py
    - omega_prime/tests/test_grokbot_emulator.py
key-decisions:
  - "A failing doctor check aborts a launch with exit 3 (strict is the default for SSE); warnings never abort."
  - "`--dry-run` mints and persists nothing: a generated token is reported as the auth source only."
  - "Doctor reports connector secrets by name only; token strength reports length, never the value."
  - "The emulator's approval scenario runs only under `--smoke` so `run_smoke_suite()` keeps its four documented scenarios."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 62-06 Launcher, doctor, emulator

Commit `b6392ad` (rebased: `9e4d0c3`). Requirements: GRK-07, GRK-09.

## What shipped

The launcher no longer exports `http://0.0.0.0:8000/sse` for a wildcard bind (it rewrites to loopback or
uses `--public-url`), no longer starts after a failed preflight, and no longer needs the token on argv
(`--token-file`, `--token-env`, `--generate-token`; argv works but warns). The doctor binds the configured
host for the port check. The emulator calls `call_tool_handler` with the scope and audit interceptors and a
`Principal("emulator", read+call)`, so roster, seat policy, approval gates and audit match the remote host.

## Verified

`oneclick --dry-run --transport sse --port 59125` exits 0; `./scripts/grokbot-1click.sh --transport stdio
--dry-run` exits 0; a real launch with `--generate-token --token-file F` prints the token once on stderr,
writes F with mode 0600 and serves (401 without a token, 200 with one); `emulator --smoke` passes six
scenarios and `x_post` is refused without approval and passes the gate (rejected for missing arguments,
so nothing is sent) with it; doctor `--json` reports 15 checks and only the expected port warning here.
