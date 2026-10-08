---
phase: 11-memory-unification
plan: 01
subsystem: memory
tags: [memory, omp, hindsight, mnemopi]
provides:
  - Omp, hindsight, and mnemopi call shapes on one MemoryStore
affects: [12-providers-and-install-surface]
---

# Phase 11 summary

`OmpMemory` speaks the Omp retain/recall/edit/forget verbs against a caller-supplied `MemoryStore`, with recall as a deterministic case-insensitive substring match over both targets. `Hindsight` and `Mnemopi` persist bank-tagged entries (`[hindsight:{bank}]`, `[mnemopi:{bank}:{id}]`) into that same store's `memory` target; banks never match each other, tags are stripped from results, and mnemopi ids (`mem-N`) survive reloads without reuse. A value added through the Hermes `memory` tool call reads back through the Omp recall, and an Omp edit shows in the Hermes render. No registry tools were added, so the roster is unchanged.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `87 passed in 3.54s` (`test_memory_unified.py`: 5 passed)

Unverified: SQLite job queues, vector embeddings, LLM extraction, reranking, consolidation, and the MCP servers.
