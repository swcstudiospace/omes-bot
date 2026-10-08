---
phase: "47"
slug: "lint-types"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# State-B reconstruction 2026-10-07: no *-VALIDATION.md existed; rebuilt from
# 47-01-PLAN.md, 47-01-SUMMARY.md, 47-VERIFICATION.md (all status: passed) plus
# parent gate receipts (ruff clean, mypy 0 errors / 174 files, suite 344 green).
# This agent ran no commands and generated no new tests; statuses below record
# historical exit-0 runs, not new runs.
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-07"
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omes/tests`) |
| **Config file** | `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, `dev` extra) |
| **Quick run command** | `.venv/bin/ruff check omes/ && .venv/bin/ruff format --check omes/` |
| **Full suite command** | `.venv/bin/python -m pytest omes/tests -q -p no:cacheprovider` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/ruff check omes/` + `.venv/bin/ruff format --check omes/`
- **After every plan wave:** Run full suite + `.venv/bin/mypy omes/` + evals + assemble
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds (mypy over `omes/` dominates)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | HYG-01, HYG-02, HYG-03 | — | Pinned Ruff/mypy load declared configuration and verify the actual code | executable gates | `.venv/bin/ruff check omes/`, `.venv/bin/ruff format --check omes/`, `.venv/bin/mypy omes/` | ✅ | ✅ green; obsolete configuration-copy tests removed during Phase 52 audit cleanup |
| 47-01-02 | 01 | 1 | HYG-01 | — | Zero `ruff check` errors; behavior changes forbidden (lint/type fixes only) | lint | `.venv/bin/ruff check omes/` | ✅ | ✅ green (hist. clean; parent receipt: all checks passed) |
| 47-01-03 | 01 | 1 | HYG-02 | — | Zero `ruff format --check` drift (119 files reformatted at the time) | lint | `.venv/bin/ruff format --check omes/` | ✅ | ✅ green (hist. 204 clean; final parent receipt: 205 formatted) |
| 47-01-04 | 01 | 1 | HYG-03 | — | Zero mypy errors on `omes/` (153→0 over 173 files at the time; honest fake/signature types, 7 targeted `type: ignore`s) | types | `.venv/bin/mypy omes/` | ✅ | ✅ green (final parent receipt: no issues in 174 source files) |
| 47-01-05 | 01 | 1 | HYG-01, HYG-02, HYG-03 | — | `lint` + `types` CI jobs install `.[dev]` and run the gates | gate | CI `lint`/`types` jobs in `.github/workflows/ci.yml` | ✅ | ✅ green (jobs present: `ruff check`, `ruff format --check`, `mypy`) |
| 47-01-06 | 01 | 1 | HYG-01, HYG-02, HYG-03 | — | Suite + evals + assemble stay green after lint/type fixes (commit `0fa783f`) | unit/eval | `.venv/bin/python -m pytest omes/tests -q` + evals + assemble | ✅ | ✅ green (hist. 315 passed / 23 evals; final suite 344 green) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: final parent receipts show actual Ruff lint/format and
mypy commands exit 0. CI declarations were inspected but CI execution was
not observed. Phase 52 removed source/configuration-copy tests, including
`test_lint_types.py`; real SDK behavior remains covered by `test_mcp_server.py`.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] Ruff lint/format and mypy executables — exercised on the actual source tree
- [x] `pyproject.toml` — ruff/mypy/dev-extra config (verified present)
- [x] `.github/workflows/ci.yml` — `lint` + `types` jobs (verified present)

---

## Manual-Only Verifications

All phase behaviors have automated verification. No manual-only items.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or procedural (commit) evidence
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** reconstructed 2026-10-07 (historical gates exit 0; current ruff/mypy/suite receipts green)
