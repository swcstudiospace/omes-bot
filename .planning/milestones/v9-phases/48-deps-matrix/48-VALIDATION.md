---
phase: "48"
slug: "deps-matrix"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# Historical State-B reconstruction retained the original 48-01 evidence.
# Those exit-0 receipts and the simulated ImportError probe are historical,
# not actual Python 3.13/3.14 full-suite or matching-head CI acceptance.
# Focused Matrix 1 reconciliation: real 3.13.14/3.14.6 runtimes now exist.
# Main exercised ordinary Discord imports, the named guard and pip check
# on both; final candidate-bound full gates and hosted receipts remain pending.
# No simulation-as-runtime acceptance, waiver or deferral is authorized.
# 48-02 validate-phase audit (2026-10-07): partial. Receipt automation exists and
# passed source/static checks; hosted/runtime acceptance stays manual-only below.
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-10-07"
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 (`[tool.pytest.ini_options]`, testpaths `omega_prime/tests`) |
| **Config file** | `pyproject.toml` (floors, `requires-python >= 3.11`, 3.12–3.14 classifiers) |
| **Quick run command** | `.venv/bin/python -m pytest omega_prime/tests/test_deps_matrix.py omega_prime/tests/test_discord.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **While implementation writers are active:** Author assigned regressions; do not run tests, builds, linters, formatters, or gates.
- **After all writers stop:** Main runs the affected acceptance union once in each actual interpreter environment, including full suite, evals, assembly, Ruff format/check, mypy, and pip check.
- **Before `/gsd-verify-work`:** Candidate-bound local gates and required matching-head hosted verify/lint/types jobs must all pass.
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 48-01-01 | 01 | 1 | HYG-04 | — | Declared floors and exact lock remain present; installed dependency set and real SDK consumers work | executable environment + suite | `.venv/bin/python -m pip check` + full suite | ✅ | ✅ green (no broken requirements; 344 tests passed); historical floor evidence preserved |
| 48-01-02 | 01 | 1 | HYG-04 | — | Committed lockfile and documented installation remain available | artifact + environment | `requirements-lock.txt`, setup docs, `.venv/bin/python -m pip check` | ✅ | ✅ present / consistent; no fresh installation claimed |
| 48-01-03 | 01 | 1 | HYG-05 | — | Discord import guard: try/except in tools + tests; fail-soft factory raises `DiscordError`; real-client test skips when unimportable | unit | `.venv/bin/python -m pytest omega_prime/tests/test_discord.py -q` | ✅ | ✅ green (hist. exit 0; sim probe: 315 passed + 1 version-gated skip) |
| 48-01-04 | 01 | 1 | HYG-05 | — | Required CI matrix includes 3.12/3.13/3.14; real final-candidate suite and hosted outcomes must be observed | hosted/runtime validation | Actual matrix execution on the final v9 tree | configured | pending: real 3.13.14/3.14.6 import/guard/pip diagnostics passed; final full gates and matching-head CI remain required |
| 48-01-05 | 01 | 1 | HYG-06 | — | MCP major cap declared; actual SDK schema/error behavior and spec note remain correct | SDK behavior | MCP tests within the full suite; `.venv/bin/python -m omega_prime.setup_check --root .` | ✅ | ✅ green; incidental pin/spelling proxies removed |
| 48-01-06 | 01 | 1 | HYG-04, HYG-05, HYG-06 | — | Full gates green + historical commit `ca48e4d` | unit/eval | suite + evals + assemble + ruff + mypy | ✅ | ✅ green (hist. 321 passed / 23 evals; final suite 344 green) |
| 48-02-00 | 02 | 1 | HYG-05 | — | Main freezes the pre-dispatch baseline (porcelain plus five SHA-256) before the sole CI writer is released | artifact | `test -f .planning/phases/48-deps-matrix/48-02-BASELINE.md` | ✅ | ✅ green (exit 0; baseline SHA-256 `e223a4e5…e45d`) |
| 48-02-01 | 02 | 1 | HYG-05 | T-48-02-01..03, T-48-02-SC | Receipt tracer: fail-fast false ×3, interpreter-bound pip, identity/pip/import receipts, `-rA`/JUnit named guard, exit propagation, `always()` five-state summaries; sole-writer scope proven against the baseline | static + scope | Plan Task 1 `<automated>` ×5 + `actionlint -no-color -oneline .github/workflows/ci.yml` | ✅ | ✅ green, source/static only. Diff 469+/9−. Scope: only ci.yml (A11) and the baseline (Main) were added. Invariants unchanged. `actionlint` exit 0. Hosted execution pending (manual-only) |
| 48-02-02 | 02 | 1 | HYG-04, HYG-05, HYG-06 | — | Main plan-conformance SUMMARY | artifact | `ls .planning/phases/48-deps-matrix/48-02-SUMMARY.md` | ✅ | ✅ green (exit 0) |
| 48-02-G | 02 | 1 | HYG-04, HYG-06 | — | Execute-phase post-merge and regression gates on the current dirty candidate (`.venv` Python 3.12.3 only) | unit | `python -m pytest -x -q --tb=short` (post-merge); prior-phase regression set (6 files) | ✅ | ✅ green: 344 passed (exit 0); regression 25 passed (exit 0). Single lane, not the 3-lane union |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence grounding: `test_deps_matrix.py` retains the real missing-Discord
subprocess failure regression; `test_discord.py` covers the controlled
factory error. Phase 52 removed version/configuration-copy assertions.
Historical declared matrix/floors/lock, installed consistency, and SDK consumer
receipts remain above. New Main diagnostics on real CPython 3.13.14 and
3.14.6 each observed ordinary installed Discord/product imports, the named
missing-library guard, and interpreter-bound `pip check` exiting 0.
`local://omega-p48-real-runtime-diagnostics.json` contains the actual commands,
identity, exits, and private log references. This is pre-implementation
dirty-worktree smoke evidence, not final full-suite or hosted acceptance.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] `omega_prime/tests/test_deps_matrix.py` — actual missing-Discord import/factory regression
- [x] `omega_prime/tests/test_discord.py` — guard branch + real-client skip tests
- [x] `requirements-lock.txt` — 150-line freeze (verified present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Final-candidate local and matching-head hosted matrix | HYG-05 | Hosted job outcomes require the authorized verified branch push; installed local runtimes are available | After writers stop, record actual 3.12/3.13/3.14 environment identity and full local gates. After the verified nonforce prior-branch push, inspect all nine verify/lint/types combinations and the separate docs job, retaining actual checkout/head SHA, run attempt, job identity, raw stage exits, skips and cancellation. The named Discord guard must pass as an actual testcase, not merely through pytest exit 0. |

---

## Validation Sign-Off

- [ ] Required matrix/interpreter outcomes observed; automation exists but its named runtime acceptance is not yet validated
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [ ] `nyquist_compliant: true`: actual matrix/interpreter validation remains pending

**Approval:** partial 2026-10-07. Historical 3.12 gates remain; new real 3.13.14/3.14.6 import/guard/pip diagnostics pass. Final candidate-bound local full gates and hosted matrix acceptance remain unverified, not waived.

## Validation Request

`48-VERIFICATION.md` remains `human_needed` until final candidate-bound local
and matching-head hosted evidence is complete. Interpreter availability is
resolved; the remaining gap is executed acceptance, not discovery.
The user selected Matrix 1, so no deferral or simulation substitution is
authorized. Keep HYG-05 partial and `nyquist_compliant: false` until the
canonical verification/validation workflow accepts actual receipts.

## Focused Receipt Rules

- Sole CI writer: `Tutmu-p48-ci-receipts`, limited to `.github/workflows/ci.yml` after its focused GSD plan/checker gate; no replay of completed 48-01 implementation.
- Required stage states: `passed`, `failed`, `skipped`, `not_run`, `cancelled`; preserve raw Actions status/conclusion and the actual reason. Use a null exit only when no command exit was observed.
- Bind pip identity, installation inputs, resolved distributions, imports and gates to the same real interpreter environment. A 3.12 snapshot lock is not cross-version proof.
- Preserve command failure propagation and explicit skipped-stage summaries; no `continue-on-error`, version spoofing, masked import failure, or fabricated exit.
- Phase 46 runtime security and pre-push secrets checks precede publication. Hosted push-triggered evidence follows that push; it is not a circular prerequisite for the first authorized branch publication.

## Validation Audit 2026-10-07 (48-02)

| Metric | Count |
|--------|-------|
| Gaps found | 0 new (HYG-05 hosted/3-lane acceptance was already manual-only) |
| Resolved | 0 |
| Escalated | 0 |

No test files were generated: the plan forbids new tests, and the remaining HYG-05 gap is runtime/hosted execution, not missing test coverage. `nyquist_compliant` stays `false` until Main records the stopped-writer 3.12/3.13/3.14 union and the matching-head hosted 9 jobs plus docs.
