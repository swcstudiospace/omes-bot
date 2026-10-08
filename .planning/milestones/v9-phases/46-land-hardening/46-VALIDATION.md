---
phase: "46"
slug: "land-hardening"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# State-B reconstruction 2026-10-07: no *-VALIDATION.md existed; rebuilt from
# 46-01-PLAN.md, 46-01-SUMMARY.md, 46-VERIFICATION.md (all status: passed) plus
# parent gate receipts (344 passed after proxy-test cleanup). This agent ran no commands and generated
# no new tests; statuses below record historical exit-0 runs, not new runs.
status: validated
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-07"
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omega_prime/tests`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Full suite command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Measured runtime** | 24.49 seconds (final parent full-suite receipt: 344 passed) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider`
- **After every plan wave:** Run full suite + `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | LAND-01 | T-46-08, T-46-12 | Redaction, intake leases, store writes, and canonical-literal URL refusals have tests; resolved fetch destinations and subsequent browser requests remain unguarded | unit + security gap | `.venv/bin/python -m pytest omega_prime/tests/test_lead.py omega_prime/tests/test_tools.py omega_prime/tests/test_credentials.py omega_prime/tests/test_systems.py omega_prime/tests/test_web.py omega_prime/tests/test_mobile.py omega_prime/tests/test_infra.py omega_prime/tests/test_quality.py -q` | ✅ | ⚠️ existing tests green; two blocking SSRF controls/regressions missing |
| 46-01-02 | 01 | 1 | LAND-02 | — | Skill/routine/doc touch-ups compose: roster/policy/template composition + catalog drift covered | unit | `.venv/bin/python -m pytest omega_prime/tests/test_harness.py omega_prime/tests/test_packs.py omega_prime/tests/test_ultrathink.py -q` | ✅ | ✅ green (hist. exit 0) |
| 46-01-03 | 01 | 1 | LAND-01, LAND-02 | — | Evals + prompt assembly stay green after landing | eval | `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` + `bash omega_prime/scripts/assemble-prompts.sh --check` | ✅ | ✅ green (hist. 23 passed; assemble up to date) |
| 46-01-04 | 01 | 1 | LAND-01, LAND-02 | — | Setup smoke: registry serves roster; tree clean post-commit | procedural | `.venv/bin/python -m omega_prime.setup_check --root .` + `git status --short` | ✅ | ✅ green (hist. setup ok; commit `f508070`) |
| 46-01-05 | 01 | 1 | LAND-01, LAND-02 | — | Docs/summary bookkeeping (no behavior) | procedural | n/a — ROADMAP + STATE updated | ✅ | ✅ green (hist. done) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: mapped test files all exist (`test_credentials.py`,
`test_tools.py`, `test_lead.py`, `test_systems.py`, `test_web.py`,
`test_mobile.py`, `test_infra.py`, `test_quality.py`, `test_ultrathink.py`,
`test_harness.py`, `test_packs.py`). Current parent gate receipt holds the
whole suite green at 344 passed after removal of incidental proxy tests.
Existing behavioral checks remain green; they do not verify the resolved-
destination or browser-request controls missing under T-46-08/T-46-12.

---

## Wave 0 Requirements

Existing tests cover the original examples; two security-derived regressions are missing.

- [x] `omega_prime/tests/` — focused behavior tests per landed hunk (fakes extended: `FakeRailway.deployment`, `AmbiguousAsc`, `FakeRunner` cwds)
- [x] `omega_prime/evals/cases` — 23-case battery via `omega_prime.evals.runner`
- [x] `pyproject.toml` pytest config — present
- [ ] Hermetic resolved-destination/peer refusal regression for T-46-08
- [ ] Hermetic browser redirect/frame/subresource refusal regression for T-46-12

---

## Manual-Only Verifications

No live verification is required. The two security-derived gaps need automated
hermetic regressions, not manual live probes. Historical PyRIT home-write
isolation is covered by Phase 51's Linux tests.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or procedural (commit/docs) evidence
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [ ] Full Nyquist coverage: two SSRF controls and regressions remain missing

**Approval:** partial 2026-10-07. Historical gates passed; final suite has 344 passes, but security-derived T-46-08/T-46-12 block advancement.

## Security-derived validation gaps

| Threat | Missing behavior | Current evidence | Disposition |
|--------|------------------|------------------|-------------|
| T-46-08 | Reject non-public resolved destinations and constrain the connected peer | Source-level high finding; current URL tests only cover canonical literals/lexical hosts | Open; user decision required |
| T-46-12 | Apply destination policy to every browser redirect/frame/subresource/navigation | Source-level high finding; fake-page tests do not cover browser egress | Open; user decision required |

No attack or live-network probe was executed. `46-SECURITY.md` records the full findings; no risk acceptance is implied.
