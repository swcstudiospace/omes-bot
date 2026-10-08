---
phase: 46-land-hardening
verified: 2026-10-07
status: gaps_found
score: 4/4 historical criteria verified; 2 blocking security gaps
gaps:
  - id: T-46-08
    truth: "Fetch connects only to validated public destinations."
    status: failed
    reason: "Source-level control gap: host spelling is checked, but DNS results and the actual peer are not constrained."
    artifacts:
      - path: omes/tools/webpack.py
        issue: "Real urllib resolution/connection bypasses destination validation."
    missing:
      - "Validate resolved destinations and constrain the connected peer against rebinding."
      - "Hermetic refusal regressions for non-public DNS results and alternate address forms."
  - id: T-46-12
    truth: "All browser requests obey the destination policy."
    status: failed
    reason: "Source-level control gap: the guarded probe does not constrain later browser requests."
    artifacts:
      - path: omes/tools/webpack.py
        issue: "Rendered review starts a second unrestricted network consumer."
      - path: omes/tools/playwright_browser.py
        issue: "No enforcement for redirects, frames, subresources, or subsequent navigation."
    missing:
      - "Enforce destination/peer policy for every browser request, or require enforced egress sandboxing."
      - "Hermetic browser request-refusal regressions independent of the initial probe."
---

# Verification: Phase 46 Land in-flight hardening

**Current status:** gaps_found — continuation security audit. Historical criteria/command receipts below are preserved, not presented as fresh security proof.
**Date:** 2026-10-07

## Success criteria

1. `pytest omes/tests -q` passes with the landed changes (no new skips) —
   PASS (310 passed, 305 carried + 5 new; HOME redirected for the sandbox
   PyRIT write, real fix in Phase 51).
2. `omes.evals.runner` passes and `assemble-prompts.sh --check` passes —
   PASS (23 evals, assemble up to date).
3. Roster/policy/template composition tests cover every touched name —
   PASS (suite green incl. composition + catalog drift test).
4. Working tree contains no uncommitted v9-previous edits — PASS (commit
   `f508070`; only v9 `.planning/` setup edits remain, uncommitted per
   `commit_docs=false`).

## Commands

- `HOME=/tmp/fakehome .venv/bin/python -m pytest omes/tests -q` → exit 0, 310 passed.
- `HOME=/tmp/fakehome .venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 23 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- `HOME=/tmp/fakehome .venv/bin/python -m omes.setup_check --root .` → exit 0.

## Historical Requirements

- LAND-01: Done. LAND-02: Done.

## Continuation audit — 2026-10-07

Final parent runtime gates pass: 344 tests, 26 evals, assembly, Ruff lint/
format (205 files), mypy (174 files), setup (108 served tools), catalog, and
pip check. Passing existing tests does not close two high source-level SSRF
control gaps from the retroactive ASVS L1 audit:

- T-46-08: fetch validates spelling/literals, not all resolved destinations
  or the actual connected peer.
- T-46-12: rendered review's initial guarded probe does not constrain later
  browser redirects, frames, subresources, or navigation.

`46-SECURITY.md` records evidence and required mitigations. `46-VALIDATION.md`
is partial: both controls and their hermetic regressions are missing.
LAND-01 has partial implementation and unsatisfied current security acceptance; LAND-02 remains satisfied.
No attack/live probe was executed and no high risk was accepted. Historical
completed plans must not be rerun wholesale; user disposition is required
before scoped mitigation work or milestone advancement.

## Current Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LAND-01 | 46-01 | In-flight tool hardening with green gates | UNSATISFIED — partial implementation | T-46-08/T-46-12 are open high hardening gaps; existing passing tests do not cover them |
| LAND-02 | 46-01 | Skill/routine/docs and roster/policy/template composition | SATISFIED | Composition, assembly, setup and catalog checks remain green and unaffected |
