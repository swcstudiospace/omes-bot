---
phase: 05-delegation-and-cron
plan: 01
subsystem: agent
tags: [delegate, cron, child]
provides:
  - Isolated child delegate and a due-job tick
affects: [06-remaining-hermes-tools]
---

# Phase 5 summary

`delegate_task` runs a child `Agent` through `run_conversation`. The parent tool row receives that child's `final_response`. The child's tool messages stay on the child transcript. The child tool map is a new dict; `parent.tools` is the same dict and the same callables after the call. Depth and batch size refuse before a child is built. A leaf child's map has no `delegate_task`. `background=True` returns a handle, and `join_delegate` runs the child once. `JobStore.tick` runs a due job through `run_conversation` and stores `final_response`. A later job waits. A one-shot does not run again. An interval job is due again at `now + interval_seconds`.

The roster lists the coding tools, the four growth tools, then `delegate_task`.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `41 passed in 0.23s`

Unverified: no live model. Background handles are process-local. Gateway delivery was not ported.

## Deferred

- A background handle keeps the parent object after join.
- `child_tool_hook` lets a test pop a key on the child tool dict. Production agents do not set it.
- `tick` writes the file after the whole pass. A runner exception can leave earlier jobs complete in memory and incomplete on disk.
