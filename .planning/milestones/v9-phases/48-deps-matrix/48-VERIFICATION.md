---
phase: 48-deps-matrix
verified: 2026-10-07T16:30:00Z
status: human_needed
score: 5/9 must-haves verified
covered_files:
  - .planning/phases/48-deps-matrix/48-01-PLAN.md
  - .planning/phases/48-deps-matrix/48-02-PLAN.md
  - .planning/phases/48-deps-matrix/48-01-SUMMARY.md
  - .planning/phases/48-deps-matrix/48-02-SUMMARY.md
  - .planning/phases/48-deps-matrix/48-CONTEXT.md
  - .planning/phases/48-deps-matrix/48-VALIDATION.md
  - .planning/phases/48-deps-matrix/48-SECURITY.md
  - .planning/phases/48-deps-matrix/48-REVIEW.md
  - .planning/phases/48-deps-matrix/48-02-BASELINE.md
  - .planning/phases/48-deps-matrix/COVERAGE.md
  - .planning/REQUIREMENTS.md
  - pyproject.toml
  - requirements-lock.txt
  - .github/workflows/ci.yml
  - omes/tools/discord.py
  - omes/tests/test_deps_matrix.py
  - docs/tool-host.md
covered_digest: "v1:sha256:49b912ab60daf29a57f82aaefc2244be44d514f3ed5d2663f965cc94a61149da"
behavior_unverified: 2
overrides_applied: 0
re_verification: true
previous_status: human_needed
previous_score: 2/4 criteria verified; real CI/interpreter outcomes unverified
gaps_closed: []
gaps_remaining: []
regressions: []
behavior_unverified_items:
  - truth: "CI matrix runs the suite on 3.12, 3.13, and 3.14 (floor stays 3.11)."
    test: "After the authorized nonforce prior-branch push, inspect the hosted run for that exact head."
    expected: "All 9 verify/lint/types combinations plus the separate 3.12 docs job complete with recorded exits; the named guard testcase passes in the suite JUnit."
    why_human: "Matrix config is present and wired, but no hosted run for a pushed matching head exists yet (publication waits Phase 46 security + pre-push secrets). Presence cannot prove hosted behavior."
  - truth: "`import omes.tools.discord` and the suite pass on 3.13+ (audioop-safe)."
    test: "Run the stopped-writer real 3-lane union: identity, install, imports, full suite with the named guard testcase, evals, assembly, Ruff, mypy, pip check on actual 3.12/3.13/3.14 interpreters."
    expected: "Guard fails soft (DiscordError) where discord is unimportable; full suite green on each lane."
    why_human: "Real 3.13.14/3.14.6 import/guard/pip-check smoke passed, but the full suite on 3.13+ was never run and the stopped-writer 3-lane union has not run. Smoke is not suite proof."
human_verification:
  - test: "Inspect the hosted 9-combination + docs run for the pushed matching head."
    expected: "All 9 verify/lint/types jobs plus docs complete; named guard testcase passed; exits recorded."
    why_human: "Hosted run does not exist yet; requires authorized push + Actions evidence collection."
  - test: "Run the stopped-writer real 3-lane union on actual 3.12/3.13/3.14 interpreters."
    expected: "Full suite (with named guard), evals, assembly, Ruff, mypy, pip check green per lane."
    why_human: "Only single-lane 3.12 full gates (344 passed) and 3.13/3.14 import/guard/pip smoke exist; full 3-lane union not executed."
  - test: "Confirm adjacent-lane isolation on the hosted run (one failing combination does not cancel siblings, yet still fails the workflow)."
    expected: "fail-fast:false retains sibling receipts; workflow conclusion still fails."
    why_human: "Backstop truth (48-02 must_haves): no hosted failure-observation exists to confirm runtime behavior; config text alone is insufficient."
  - test: "Confirm empty-install-input impossibility on the hosted run (every matrix job installs before gating; failed install records dependents as not_run, never passed)."
    expected: "Receipt summaries show not_run for dependents of any failed install; no pass without install."
    why_human: "Backstop truth (48-02 must_haves): confirmable only by observed hosted stage states, not by workflow text."
---

# Phase 48: Deps Matrix Verification Report (re-verification, gaps-only)

**Phase Goal:** Reproducible installs on every supported Python.
**Verified:** 2026-10-07T16:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after 48-02 gap-closure round (prior: human_needed, 2/4 criteria)

Prior history is preserved: the pre-update report lives at
`local://omega-p48-pre-tail-48-VERIFICATION.md`. This report re-verifies
from the codebase; SUMMARY claims were checked against files, not trusted.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dependency floors raised to verified versions with a committed lockfile (SC-1) | ✓ VERIFIED | `pyproject.toml:8,22-29`: `requires-python >=3.11`, 8 floors (tweepy 4.17, mcp 2.3 cap `<3`, pyrit 1.1, apscheduler 3.11, aiogram 3.31, discord.py 2.7, playwright 1.63, Appium 6.0). `requirements-lock.txt`: 150 lines, pins all 8 directs + mcp 2.3.0. Genuine Main log `local://omega-p48-post-merge-test-gate.log`: 344 passed on .venv 3.12.3; `pip check` clean per 48-VALIDATION. |
| 2 | CI matrix runs the suite on 3.12, 3.13, 3.14; floor stays 3.11 (SC-2) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Config present + wired: `ci.yml` verify/lint/types each `python-version: ["3.12","3.13","3.14"]` + `fail-fast: false`; docs stays 3.12-only; triggers push + pull_request; floor `>=3.11` unchanged. But the hosted 9-combination + docs run for a pushed matching head does not exist (publication precedes it). |
| 3 | `import omes.tools.discord` and the suite pass on 3.13+ (SC-3) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Guard present + wired: `omes/tools/discord.py:16-19` try/except → None; `_default_client` raises DiscordError; `test_deps_matrix.py` real-subprocess guard regression retained. Genuine Main diagnostics `local://omega-p48-real-runtime-diagnostics.json`: real CPython 3.13.14/3.14.6 ordinary installed-discord + product imports, named guard, and `pip check` all exit 0 — but classified in-file as dirty-tree smoke, not full-suite proof. Full suite on 3.13+ never run. |
| 4 | `mcp>=2,<3` pinned, no v1-isms, conformance recorded (SC-4) | ✓ VERIFIED | `pyproject.toml:23` `mcp>=2.3,<3`; `docs/tool-host.md:21-24` records spec 2026-07-28 (v2 snake_case Python, camelCase wire); lock pins mcp 2.3.0; MCP tests pass inside the genuine 344-test gate. |
| 5 | Sole A11 writer owns ci.yml; matrices, commands, docs job, triggers preserved (48-02 T1) | ✓ VERIFIED | ci.yml diff vs HEAD: 1 file, 469+/9−, all in `.github/workflows/ci.yml`. Genuine A11 record `local://Tutmu-p48-ci-receipts.result.json`: `changed_files: [".github/workflows/ci.yml"]`, state IN_REVIEW, source-only, no checks run by writer. Triggers, matrix values, original gate commands, separate 3.12 docs job intact in source. |
| 6 | CI delta is the accepted minimal receipt tracer only (48-02 T2) | ✓ VERIFIED | Added lines: `fail-fast: false` ×3, 12 `python3 -m pip` lines, identity/pip/import receipts, suite `-rA --junitxml` with named guard testcase parse, per-command exit propagation, always-run summaries. `actionlint` exit 0, yaml parse + 6 heredoc compiles pass per 48-02-SUMMARY. 48-REVIEW.md: 0 critical, 1 warning (falsy exit-code mapping, routed to CI writer), 1 info (triplication drift). |
| 7 | Four read-only invariants byte-identical to Task 0 baseline (48-02 T3) | ✓ VERIFIED | Current SHA-256 of pyproject.toml, requirements-lock.txt, test_deps_matrix.py, discord.py all equal `48-02-BASELINE.md` §(b) entries (`ea4763a7…`, `9c285986…`, `9d784f92…`, `fdc18221…`). |
| 8 | Adjacent-lane isolation backstop (48-02) | ⚠️ INSUFFICIENT_SPEC → human item 3 | `verification: backstop` non-inferable truth; no hosted failure observation exists. Abstained per backstop rule, recorded as human verification, never a silent pass. |
| 9 | Empty-install-input impossibility backstop (48-02) | ⚠️ INSUFFICIENT_SPEC → human item 4 | Same backstop handling; confirmable only by observed hosted stage states. |

**Score:** 5/9 truths verified (2 present-but-behavior-unverified, 2 backstop-pending-hosted)

### Deferred Items

None. No later milestone phase covers 48's hosted matrix / 3-lane union
(phases 49–52 are provider/evals scope). HYG-05 stays partial here, not deferred.

### Advisory

None. One re-verification-scope note: `48-REVIEW.md` WR-01 (falsy
`int(exit_code) if exit_code else None` in three receipt scripts) is a
latent evidence-corruption risk routed to the sole CI writer, not fixed in
this round — recorded, not blocking, since current string-typed outputs map
correctly.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | floors, mcp cap, 3.11 floor, 3.13/3.14 classifiers | ✓ VERIFIED | Substantive, wired (CI installs from it) |
| `requirements-lock.txt` | committed exact snapshot | ✓ VERIFIED | 150 lines, all 8 directs pinned |
| `.github/workflows/ci.yml` | 3.12–3.14 matrices + receipt tracer | ✓ VERIFIED | 528 lines, matrices + tracer + docs job intact |
| `omes/tools/discord.py` | import guard + fail-soft factory | ✓ VERIFIED | Substantive, wired (imported by receipt + tests) |
| `omes/tests/test_deps_matrix.py` | guard regression | ✓ VERIFIED | Real-subprocess DiscordError-branch test retained |
| `docs/tool-host.md` | MCP v2 conformance note | ✓ VERIFIED | Spec 2026-07-28 conventions recorded |
| `48-02-BASELINE.md` | pre-dispatch provenance snapshot | ✓ VERIFIED | Porcelain + 5 hashes + write sets, immutable |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| ci.yml matrix | hosted 9 verify/lint/types + docs | Main push + Actions collection | NOT YET OBSERVED | Config wired; run does not exist — human item 1 |
| suite `-rA`/JUnit | named guard testcase | receipt-script JUnit parse | WIRED IN SOURCE | `test_discord_module_imports_without_the_library` parsed; observed only in 3.12 lane + 3.13/3.14 smoke |
| discord guard | suite green on 3.13+ | full 3-lane union | NOT YET OBSERVED | Smoke only — human item 2 |
| pyproject floors | fresh-resolve install | interpreter-bound pip | WIRED IN SOURCE | Install inputs unchanged; fresh-install claim not made |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Real Data | Status |
|----------|---------------|--------|-----------|--------|
| ci.yml receipt summary | step exits → STAGES map | `$GITHUB_OUTPUT` exit_code per step | Source-correct (WR-01 caveat noted) | ✓ FLOWING (source) / unobserved (hosted) |
| requirements-lock.txt | exact pins | 3.12 freeze | Real 3.12 snapshot; not cross-version proof | ✓ FLOWING with stated limit |

### Behavioral Spot-Checks

Step 7b: SKIPPED as execution (read-only contract: no installs, tests, or
gate runs by this verifier). Consumed Main's genuine recorded evidence
read-only: post-merge gate 344 passed (.venv 3.12.3), regression gate 25
passed, real-runtime diagnostics 3.13.14/3.14.6 import+guard+pip-check
passed (dirty-tree smoke, not union/hosted acceptance), A11 source-only
result (no runtime claims). Nothing upgraded into 3-lane or hosted acceptance.

### Probe Execution

No `scripts/*/tests/probe-*.sh` phase-declared probes apply to Phase 48.
No probe execution required.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HYG-04 | 48-01, 48-02 | Verified floors + committed lockfile | SATISFIED | Floors + 150-pin lock present; hashes match baseline; pip check clean in genuine gate |
| HYG-05 | 48-01, 48-02 (D1 source / D2 pending) | CI matrix 3.12–3.14 + real 3.13+ behavior | PARTIAL — human validation required | Matrix config + guard + smoke verified; matching-head hosted run + stopped-writer 3-lane union missing |
| HYG-06 | 48-01, 48-02 | MCP v2 line + conformance | SATISFIED | Cap + spec note + SDK behavior in genuine suite |

No orphaned IDs: every HYG-04/05/06 mapping in REQUIREMENTS.md §Traceability
is claimed by a Phase 48 plan, and every plan-declared ID maps back.
REQUIREMENTS.md itself records HYG-05 as Partial — consistent with this verdict.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| omes/tools/discord.py, test_deps_matrix.py | TBD/FIXME/TODO/stub/empty-return scan | — | None found |
| .github/workflows/ci.yml | `continue-on-error` / `\|\| true` / literal `exit 0` | — | None found (capture-and-propagate only) |

### Human Verification Required

Four items (frontmatter `human_verification`): hosted 9+docs run for the
pushed matching head; stopped-writer 3-lane union; two backstop confirmations
(isolation, empty-install impossibility) observable only on the hosted run.
Prerequisites in order: writers stop → 3-lane union → Phase 46 security +
pre-push secrets → nonforce prior-branch push → hosted collection.

### Gaps Summary

No code gaps: every implementable artifact exists, is substantive, and is
wired in source. What remains is executed acceptance, not implementation:
the hosted run and the full 3-lane union cannot be produced read-only and
were not waived. HYG-05 stays partial; HYG-04/HYG-06 satisfied.

---
_Verified: 2026-10-07T16:30:00Z_
_Verifier: OmegaP48NativeVerifier (native gsd-verifier re-verification, gaps-only, read-only)_
