---
phase: 20-eval-harness
plan: 01
subsystem: evals
tags: [evals, redteam, ci]
provides:
  - Deterministic golden and red-team evals with CI
affects: []
---

# Phase 20 summary

`omega_prime/evals/runner.py` replays JSON cases: loop cases through `run_conversation` with `ScriptedModel`, registry cases through policy/approval-gated dispatch. Seven structural expectation types (final contains/not, exit reason, tool called/not, refusal text, tool-row count) keep runs deterministic with no judge. Six shipped cases pass: three golden persona checks and three red-team checks (policy escape refused, unapproved publish refused, injected tool output contained). `.github/workflows/ci.yml` runs the suite, the evals, and the assemble check on push and PR.

## Verification

Command: `python3 -m pytest omega_prime/tests -q` (plus `python3 -m omega_prime.evals.runner omega_prime/evals/cases`)

Exit code: 0 (both)

Output tail: `126 passed in 3.70s` (`test_evals.py`: 3 passed); evals `6 passed, 0 failed`

Unverified: CI minutes on GitHub runners, model-judged evals, broader red-team coverage.
