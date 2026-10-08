---
phase: 02-hermes-loop
plan: 01
subsystem: agent
tags: [loop, steer, compression, interrupt]
provides:
  - run_conversation with named turn phases
affects: [03-coding-toolset]
---

# Phase 2 summary

`omega_prime.agent.conversation_loop.run_conversation` runs a tool round or a text finish. The system prompt is built once. A steer is a new user row after the tool row. `compress_messages` is the only rewriter of earlier messages. An interrupt or a spent budget stops the loop before another model call. The default per-turn budget refills at the start of the next turn. A caller-supplied budget does not.

This is the iteration, not every Hermes `turn_*.py` file. Preflight, overflow, recovery, API-error, and the SQLite session lease stay in the Hermes checkout. The loop does not auto-compress on a token threshold. Chrome (TUI, billing, gateway) was not ported.

## Verification

Command: `python3 -m pytest omega_prime/tests/test_shell.py omega_prime/tests/test_loop.py -q`

Exit code: 0

Output tail: `19 passed in 0.08s`

Unverified: no live model provider. `ScriptedModel` drives the loop.
