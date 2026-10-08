---
phase: 19-nightly-learning
plan: 01
subsystem: routines
tags: [nightly, curator, skills]
provides:
  - Nightly transcript review creating earned skills
affects: [20-eval-harness]
---

# Phase 19 summary

`nightly_pass` maps each turn's transcript onto `review_turn` (last non-steer user row as the request, tool rows as success/output pairs), creates skills for earned turns through the skill manager, and checkpoints reviewed ids atomically after every turn so re-runs skip everything. Unearned turns write nothing but still checkpoint.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `123 passed in 4.29s` (`test_nightly.py`: 2 passed)

Unverified: cron scheduling of the pass, journal-fed transcripts, model-judged earning.
