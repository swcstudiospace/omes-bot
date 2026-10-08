---
phase: 58-connectors
verified: 2026-10-08
status: passed
score: 4/4 connector criteria verified
gaps: []
---

# Verification: Phase 58 Connector layer + parity suite

**Status:** passed
**Date:** 2026-10-08

## Success criteria

1. Every Prime capability call goes through a typed adapter with a versioned
   schema — PASS (`omega_prime/prime/` five adapters, `SCHEMA_VERSION = 1`
   each, strict `from_dict` decoders).
2. Contract tests validate request/response shapes on both sides — PASS
   (`test_prime_contracts.py`, 29 tests: round-trips, unknown-field and
   bool/int rejection, closed vocabularies, future-schema guard).
3. Failure-injection: capability raise/timeout/bad payload/unknown status →
   structured error, loop continues, no hang — PASS
   (`test_prime_failure_injection.py`, 7 tests).
4. Parity fixtures derived from the Rust baseline pass against the ported
   implementation — PASS (`tests/parity/` six source-cited fixtures +
   `test_prime_parity.py`, 6 tests).

## Commands

- `.venv/bin/python -m pytest omega_prime/tests -q` → 526 passed.
- `python -m omega_prime.evals.runner omega_prime/evals/cases` → 26 passed,
  0 failed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → up to date.
- `python -m omega_prime.tooling.catalog --check` → up to date.
- `python -m omega_prime.setup_check --root .` → registry serves 108 roster
  tools.
- `ruff check omega_prime/` + `ruff format --check` → clean.
- `mypy omega_prime/` → no issues in 215 source files.

## Requirements

- CONN-01: Done. CONN-02: Done. CONN-03: Done. CONN-04: Done.
