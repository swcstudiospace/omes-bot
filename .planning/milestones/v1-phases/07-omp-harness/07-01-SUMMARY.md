---
phase: 07-omp-harness
plan: 01
subsystem: agent
tags: [harness, events, pause, steer, output-budget, speculation]
provides:
  - Omp agent-core behavior merged into the phase 2 conversation loop
affects: [08-edit-pipeline]
---

# Phase 7 summary

A turn emits `turn_start`, one `message` per appended row, and `turn_end` with the exit reason. A `before_model` hook may mutate the outgoing request or stop the turn before it is billed (no model call, no budget spent). `PauseGate` parks the loop before each model call and each tool execution; resume finishes the turn, in-flight tool work runs to completion, and an interrupt unwinds a parked wait while the gate stays engaged. Steer text injected mid-turn — via the harness queue or the legacy slot — lands as its own user row after the tool rows, including steer injected while a tool runs. Tool results flagged `useless` persist as non-error rows; a result flagged both useless and error stays an error with no useless flag. `compress_messages` blanks useless rows with the Omp notice and never elides errors. `OutputBudget` stops a runaway turn with `output_budget_exceeded` before another model call. Discard-safe tools pre-execute once and commit on fingerprint match; a changed argument discards the prepared entry. The model still receives the caller's exact tool map, `turn_tool_round.py` and `turn_finalizer.py` are untouched, and undelivered queued steer is reported on the result's `pending_steer` key.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `60 passed in 3.42s` (`test_harness.py`: 13 passed; every `test_loop.py` check still passes)

Unverified: streaming, tokenizers, session persistence, compaction summarizers, and the TUI event bus.
