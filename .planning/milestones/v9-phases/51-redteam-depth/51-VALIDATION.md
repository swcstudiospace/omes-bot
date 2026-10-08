---
phase: "51"
slug: "redteam-depth"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# State-B reconstruction 2026-10-07: no *-VALIDATION.md existed; rebuilt from
# 51-01-PLAN.md, 51-01-SUMMARY.md, 51-VERIFICATION.md (all status: passed) plus
# parent gate receipts (final suite 344 green under isolated HOME/XDG) and source re-reads
# (conftest.py, evals/pyrit_target.py, test_pyrit_target.py). This agent ran no
# commands and generated no new tests; statuses below record historical
# exit-0 runs, not new runs.
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-07"
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omega_prime/tests`) |
| **Config file** | `pyproject.toml` + `omega_prime/tests/conftest.py` (XDG redirect pre-pyrit-import) |
| **Quick run command** | `.venv/bin/python -m pytest omega_prime/tests/test_pyrit_target.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest omega_prime/tests/test_pyrit_target.py -q`
- **After every plan wave:** Run full suite with NO `HOME=` redirect (proves DPT-01) + evals + assemble + ruff + mypy
- **Before `/gsd-verify-work`:** Full suite must be green; real-HOME `dbdata` mtime unchanged
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 1 | DPT-01 | — | `conftest.py` redirects `XDG_DATA_HOME` into tmp before any pyrit import (import-time mkdir/touch from `pyrit/common/path.py` via appdirs); suite collects/passes with no `HOME=` workaround (`conftest.py:16-19`) | unit | `.venv/bin/python -m pytest omega_prime/tests/test_pyrit_target.py -q` | ✅ | ✅ green (hist. redirect-mechanism + Linux-gated `DB_DATA_PATH`-under-redirect tests; `test_pyrit_data_dir_is_redirected_out_of_home`) |
| 51-01-02 | 01 | 1 | DPT-02 | — | `OmegaPrimePromptTarget` declares multi-turn capability, answers latest turn (single-prompt behavior identical); `run_campaign` drives one `MultiPromptSendingAttack`, pairs turns from memory, rejects empty campaigns (`pyrit_target.py:126-148`) | unit | campaign tests in `test_pyrit_target.py` | ✅ | ✅ green (hist. state-chaining + cross-turn injection campaigns) |
| 51-01-03 | 01 | 1 | DPT-03 | — | Per-turn judging with case-sensitive `SubStringScorer`s (`ExactTextMatching(case_sensitive=True)`); optional objective scorer via `AttackScoringConfig`; missing responses fail (`pyrit_target.py:47-51,203-209`) | unit | objective-outcome ×2 tests in `test_pyrit_target.py` | ✅ | ✅ green (hist. SUCCESS/FAILURE outcome marking) |
| 51-01-04 | 01 | 1 | DPT-01, DPT-02, DPT-03 | — | Full gates green; PyRIT memory in-memory/file-isolated; pre-existing `~/.local/share/dbdata/logs.txt` untouched (commit `36fd803`) | unit/eval | historical suite (no HOME redirect) + evals + assemble + ruff + mypy | ✅ | ✅ green (hist. 350 passed / 23 evals; final 344-passed suite used an isolated HOME/XDG) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: `omega_prime/tests/conftest.py` (XDG redirect) and
`omega_prime/tests/test_pyrit_target.py` (isolation + campaign + scorer tests)
exist; scorer/campaign wiring re-confirmed in `omega_prime/evals/pyrit_target.py`
(`SubStringScorer`, `MultiPromptSendingAttack`, `AttackScoringConfig`,
`run_campaign`). macOS appdirs-XDG caveat is documented in the plan, not a
hidden gap. No new tests were generated for this reconstruction.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] `omega_prime/tests/conftest.py` — XDG redirect before pyrit import
- [x] `omega_prime/tests/test_pyrit_target.py` — isolation + campaign + objective-outcome tests (keyless, deterministic)
- [x] `omega_prime/evals/pyrit_target.py` — target + `run_campaign` + case-sensitive judging

---

## Manual-Only Verifications

All phase behaviors have automated verification. Keyed (non-keyless) PyRIT
campaign variants are opt-in live probes, out of scope for CI — not a gap
in this phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** reconstructed 2026-10-07 (historical no-HOME-redirect gates exit 0; final 344-passed suite used an isolated HOME/XDG).
