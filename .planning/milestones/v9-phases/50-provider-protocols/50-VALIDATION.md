---
phase: "50"
slug: "provider-protocols"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# State-B reconstruction 2026-10-07: no *-VALIDATION.md existed; rebuilt from
# 50-01-PLAN.md, 50-01-SUMMARY.md, 50-VERIFICATION.md (all status: passed) plus
# parent gate receipts (final suite 344 green) and source re-reads (openai.py,
# base.py, providers http/fake, test_transports.py:363). This agent ran no
# commands and generated no new tests; statuses below record historical
# exit-0 runs, not new runs.
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-07"
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omega_prime/tests`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest omega_prime/tests/test_transports.py omega_prime/tests/test_providers.py omega_prime/tests/test_loop.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run the three provider/loop test files above
- **After every plan wave:** Run full suite + evals + assemble + ruff + mypy
- **Before `/gsd-verify-work`:** Full suite must be green; no live calls in committed tests
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 1 | PCUR-03 | — | `OpenAIProvider.api_mode` auto/responses/chat_completions: auto → Responses on api.openai.com, chat elsewhere (`openai.py:27-36`); stateless `store: false`; transcript → input items; failed raises, incomplete parses | unit | `.venv/bin/python -m pytest omega_prime/tests/test_providers.py -q` | ✅ | ✅ green (hist. routing + round-trip + failed/empty/incomplete tests) |
| 50-01-02 | 01 | 1 | PCUR-03 | — | xAI/compatibles stay on chat_completions (Grok pins `api_mode`); one-shot chat fallback on 404/scope-denied with `last_fallback`; 400 and chat-mode errors surface (`base.py:69,177-182`; `openai.py:97`) | unit | fallback ×3 + routing-pin tests in suite | ✅ | ✅ green (hist. exit 0) |
| 50-01-03 | 01 | 1 | PCUR-04 | — | `Transport.stream` yields text lines; `HttpTransport` SSE iteration (retries end at first byte); `FakeTransport` replays scripted lines; per-provider `stream_request` + `parse_stream` → (row, usage?) incl. usage chunks | unit | `.venv/bin/python -m pytest omega_prime/tests/test_transports.py -q` | ✅ | ✅ green (hist. per-provider wire shapes, HTTP stream ×2, no-retry-after-first-byte, no-stream error) |
| 50-01-04 | 01 | 1 | PCUR-04 | — | Loop consumes streamed output end to end: `run_conversation` over `stream=True` `ProviderModel`; all five adapters accumulate | unit | `test_loop_consumes_streamed_output_end_to_end` (`test_transports.py:363`) + loop tests | ✅ | ✅ green (hist. exit 0; 4 streaming-accumulation tests) |
| 50-01-05 | 01 | 1 | PCUR-03, PCUR-04 | — | Full gates green; no live calls (commit `cafcf5f`); Responses streaming + reasoning continuity explicitly deferred in code | unit/eval | suite + evals + assemble + ruff + mypy | ✅ | ✅ green (hist. 344 passed / 23 evals; final suite 344 green) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: routing/fallback/streaming wiring re-confirmed in
current source (`openai.py` `effective_mode`/`fallback_request`,
`base.py` `stream_request`/`parse_stream`/`_complete_stream`,
`http.py:75-76` stream contract). Deferred items (Responses streaming,
reasoning continuity) are documented in code, not hidden gaps. No new
tests were generated for this reconstruction.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] Scripted SSE/NDJSON line fixtures + `FakeTransport.stream` replay
- [x] Scripted SSE peer for `HttpTransport.stream` (status/headers/framing)
- [x] `stream=True` `ProviderModel` loop end-to-end test

---

## Manual-Only Verifications

All phase behaviors have automated verification. Live Responses/streaming
calls against real endpoints are out of scope (hermetic rule; DEEP-03) —
not a gap in this phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** reconstructed 2026-10-07 (historical gates exit 0; final suite 344 green).
