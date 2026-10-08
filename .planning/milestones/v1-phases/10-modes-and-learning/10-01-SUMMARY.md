---
phase: 10-modes-and-learning
plan: 01
subsystem: agent
tags: [sessions, tasks, plan-mode, extensions, autolearn, goals, advisor, exec, security]
provides:
  - Session/task persistence, plan mode, extension hooks, and learning controls
affects: [11-memory-unification]
---

# Phase 10 summary

Sessions and tasks persist as versioned JSON documents with atomic writes; new handles on the same directory load them, unknown ids raise `KeyError`. Plan mode wraps the loop's tool map so write tools return a refusal without running (reads unaffected, speculation skipped, the caller's map restored after the turn). `ExtensionHooks` runs `before_model` hooks in order before the legacy hook, first stop wins. `Autolearn.consider_turn` gates on tool-call count and writes through `skill_manage` (create, then edit on conflict). `GoalStore` tracks one objective with steps on disk. The advisor renders escaped `<advisory>` blocks. `JobControl` spawns, polls, waits, and kills argv jobs, reaping each exactly once. `screen_argv` refuses escalation binaries, filesystem-wide deletes, and malformed argv, and `JobControl.start` enforces it. No registry tools were added, so the roster is unchanged.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `82 passed in 3.59s` (`test_modes.py`: 10 passed; no job left running)

Unverified: TUI modes, interactive sessions, auth, cloud security scans, variable inspection, and the learn-memory backend.
