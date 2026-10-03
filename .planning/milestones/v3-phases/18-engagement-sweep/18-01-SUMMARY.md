---
phase: 18-engagement-sweep
plan: 01
subsystem: routines
tags: [sweep, drafts, checkpoints]
provides:
  - Mention sweep producing queued drafts, resumable per mention
affects: [19-nightly-learning]
---

# Phase 18 summary

`sweep_mentions` fetches mentions once, composes one reply draft per fresh mention through an injected composer, and checkpoints `{drafted, drafts, skipped}` atomically after every mention. Interruptions resume without duplicating drafts; blank drafts are recorded skipped and never retried; id-less mentions are ignored. The sweep never publishes — drafts queue for a human or an approved job.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `121 passed in 3.78s` (`test_sweep.py`: 3 passed)

Unverified: a model-backed composer, cron scheduling of the sweep, live mentions.
