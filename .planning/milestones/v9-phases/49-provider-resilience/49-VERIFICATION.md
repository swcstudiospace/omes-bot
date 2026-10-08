---
phase: 49-provider-resilience
verified: 2026-10-07
status: passed
score: 4/4 success criteria verified
---

# Verification: Phase 49 Provider resilience

**Status:** passed
**Date:** 2026-10-07

## Success criteria

1. Transient failures retry with backoff behind FakeTransport tests — PASS
   (408/429/5xx/connection/timeout retried; 429 honors Retry-After; scripted
   socketpair peers, sleeps recorded not slept).
2. Per-turn usage recorded and asserted — PASS (`last_usage` + model spans
   carry normalized counters; junk/absent shapes yield None/omission).
3. Anthropic max_tokens raised, model defaults current — PASS (8192;
   `claude-1` → `claude-sonnet-4`; no other stale IDs in repo).
4. Suite + evals green, no live calls — PASS (330 tests, 23 evals;
   fakes + socketpairs only).

## Commands

- `HOME=/tmp/fakehome .venv/bin/python -m pytest omes/tests -q` → exit 0, 330 passed.
- `omes.evals.runner` → 23 passed. `assemble-prompts.sh --check` → exit 0.
- `ruff check`, `ruff format --check`, `mypy omes/` → clean.

## Requirements

- PCUR-01: Done. PCUR-02: Done. PCUR-05: Done.

## Continuation verification — 2026-10-07

Current parent gates: 344 tests, 26 evals, assembly, Ruff lint/format,
mypy, setup, catalog, and pip check all exit 0. Retry/usage behaviors remain
covered by the actual provider/transport/loop tests; the cross-phase
integration reviewer traced usage into streamed-turn spans with no broken
link. Historical counts above are preserved; no live provider call occurred.
Current mappings and scoped controls are in `49-VALIDATION.md` and `49-SECURITY.md`.

## Current Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PCUR-01 | 49-01 | Transient retries and backoff | SATISFIED | Historical behavioral receipts and current green provider suite; no live provider qualification |
| PCUR-02 | 49-01 | Per-turn provider usage | SATISFIED | Provider parsing and conversation-loop usage propagation remain integrated in current green suite |
| PCUR-05 | 49-01 | Updated configured defaults and documented model IDs | SATISFIED | Historical defaults update and current code/docs review; live model availability is not certified |
