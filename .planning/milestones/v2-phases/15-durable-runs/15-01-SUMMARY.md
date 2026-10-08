---
phase: 15-durable-runs
plan: 01
subsystem: durable
tags: [journal, cron, workflows, sqlite]
provides:
  - SQLite turn journal, cron history with claims, checkpointed workflows
affects: [16-transports-and-traces]
---

# Phase 15 summary

`TurnJournal` persists every transcript row to SQLite at the same snapshot points where the loop emits `message` events; crashed runs stay `open` and resume from `transcript`. Cron jobs record bounded history (20 entries, newest last), claim each tick before running, and skip claimed or completed ticks — a second tick at the same time runs nothing, and old stores backfill the new keys. `run_workflow` checkpoints `{done, state}` atomically after each step and re-running skips finished steps, so an interrupted three-step workflow resumes mid-run with completed effects unrepeated.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `110 passed in 3.66s` (`test_durable.py`: 5 passed)

Unverified: multi-process journal contention, Temporal as a later adapter, distributed cron.
