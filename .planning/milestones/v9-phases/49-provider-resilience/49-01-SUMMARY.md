---
phase: 49-provider-resilience
plan: "01"
subsystem: api
tags: [providers, retries, usage]
requirements-completed: [PCUR-01, PCUR-02, PCUR-05]
completed: 2026-10-07
status: complete
---

# Summary 49-01: Retry 408/429, usage accounting, current defaults

**Added transient-provider retries and normalized per-turn token accounting.**

## What was built

- `HttpTransport`: 408 + 429 join the retryable set; `Retry-After`
  (seconds) honored up to a 60s cap; sleep stays skipped when `backoff=0`
  so tests never wall-sleep. Headers plumbed through `_request`.
- Usage: `Provider.parse_usage` per adapter (OpenAI/Grok, Anthropic
  in/out, Gemini usageMetadata, Ollama eval counts) via a shared
  `_usage_from` guard (ints only, no synthesis); `ProviderModel.complete`
  stores `last_usage`; the loop adds it to `kind="model"` spans.
- Defaults: Anthropic `max_tokens` 4096 → 8192; `claude-1` fixture →
  `claude-sonnet-4`; base docstring corrected (retries live in transport).
- Tests: socketpair fixture gains per-attempt headers; 4 retry tests
  (408/429 success, Retry-After + cap via recorded sleeps, exhaustion,
  no-sleep-at-zero), 3 usage tests, 2 span tests. +9 total.

## Verification

Suite → exit 0, 330 passed (321 + 9). Evals → 23 passed. Assemble,
ruff, mypy green. No real sleeping in tests (recorded sleeps asserted).
Commit `efc1d66`.
