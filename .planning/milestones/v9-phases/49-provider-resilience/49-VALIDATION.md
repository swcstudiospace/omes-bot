---
phase: "49"
slug: "provider-resilience"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# State-B reconstruction 2026-10-07: no *-VALIDATION.md existed; rebuilt from
# 49-01-PLAN.md, 49-01-SUMMARY.md, 49-VERIFICATION.md (all status: passed) plus
# parent gate receipts (final suite 344 green) and source re-reads (http.py, base.py,
# conversation_loop.py). This agent ran no commands and generated no new tests;
# statuses below record historical exit-0 runs, not new runs.
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-07"
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omes/tests`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest omes/tests/test_transports.py omes/tests/test_providers.py omes/tests/test_loop.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest omes/tests -q -p no:cacheprovider` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run the three provider/loop test files above
- **After every plan wave:** Run full suite + evals + assemble + ruff + mypy
- **Before `/gsd-verify-work`:** Full suite must be green; no live calls in committed tests
- **Max feedback latency:** 60 seconds (no real sleeps; backoff skipped at `backoff=0`)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | PCUR-01 | — | 408 + 429 join the retryable set; `Retry-After` honored up to 60s cap; sleep skipped when `backoff=0`; headers plumbed through `_request` (`omes/providers/http.py:291-319`) | unit | `.venv/bin/python -m pytest omes/tests/test_transports.py -q` | ✅ | ✅ green (hist. 4 retry tests: 408/429 success, Retry-After + cap via recorded sleeps, exhaustion, no-sleep-at-zero) |
| 49-01-02 | 01 | 1 | PCUR-02 | — | `Provider.parse_usage` per adapter via shared `_usage_from` (ints only, no synthesis); `ProviderModel.complete` stores `last_usage`; loop adds it to `kind="model"` spans (`base.py:54,142,212`; `conversation_loop.py:352-356`) | unit | `.venv/bin/python -m pytest omes/tests/test_providers.py omes/tests/test_loop.py -q` | ✅ | ✅ green (hist. 3 usage + 2 span tests; e.g. `test_complete_records_last_usage`) |
| 49-01-03 | 01 | 1 | PCUR-05 | — | Anthropic `max_tokens` 4096 → 8192; `claude-1` fixture → `claude-sonnet-4`; stale base docstring corrected | unit | Anthropic-body assertion test in suite | ✅ | ✅ green (hist. exit 0; no other stale IDs in repo per verification) |
| 49-01-04 | 01 | 1 | PCUR-01, PCUR-02, PCUR-05 | — | Full gates green; fakes + socketpairs only, no live calls, no real sleeping (commit `efc1d66`) | unit/eval | suite + evals + assemble + ruff + mypy | ✅ | ✅ green (hist. 330 passed / 23 evals; final suite 344 green) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: `omes/tests/test_transports.py`, `test_providers.py`,
and `test_loop.py` exist; retry/usage wiring re-confirmed in current source
(`http.py` `_check_status`/`_retry_after`, `base.py` `parse_usage`/
`last_usage`, `conversation_loop.py` usage→span). Cross-phase link: usage
recorded here is consumed by streamed turns in Phase 50 (`_complete_stream`
sets `last_usage` the same way). No new tests were generated for this
reconstruction.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] Socketpair fixture with per-attempt headers + monkeypatched sleep recorder (hermetic retry proof)
- [x] Per-adapter `parse_usage` cases incl. unknown-shape → None
- [x] `test_complete_records_last_usage` + loop span carriage tests

---

## Manual-Only Verifications

All phase behaviors have automated verification. Live API verification lanes
are out of scope (REQUIREMENTS.md DEEP-03, needs keys + user decision) — not
a gap in this phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** reconstructed 2026-10-07 (historical gates exit 0; final suite 344 green).
