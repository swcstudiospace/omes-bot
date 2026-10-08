---
phase: 48-deps-matrix
plan: "02"
subsystem: infra
tags: [github-actions, ci, python-matrix, receipts, discord-guard]

requires:
  - phase: 48-deps-matrix
    provides: "48-01 dependency floors, lockfile, Discord import guard, MCP v2 cap (preserved, not replayed)"
provides:
  - "Receipt-instrumented CI matrix: fail-fast false, interpreter-bound pip, identity/pip/import receipts, -rA/JUnit suite with named Discord guard check, per-command exit propagation, always-run receipt summaries"
affects: [phase-48-verification, prior-branch-publication, hosted-ci-collection]

actuals:
  tokens: 11800
  tasks: 3
  commits: 0

tech-stack:
  added: []
  patterns:
    - "Capture-and-propagate step wrapper: set +e; cmd; rc=$?; print stage/exit; write exit_code output; exit $rc"
    - "Always-run per-job receipt summary mapping Actions outcome/conclusion to passed/failed/skipped/not_run/cancelled"

key-files:
  created:
    - .planning/phases/48-deps-matrix/48-02-BASELINE.md
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "Product slot bound to the existing signed A11 record Tutmu-p48-ci-receipts via the named specialized pool OmegaPhase48CIReceipts; no gsd-executor product writer."
  - "Per-task commits deferred: Main makes explicit-path commits after the stopped-writer union, per the user's ownership decision."
  - "HYG-05 stays partial: source instrumentation only; acceptance needs the real 3-lane local union and matching-head hosted evidence."

patterns-established:
  - "Baseline-relative, provenance-attributed scope proof for a single writer in an intentionally dirty worktree"

requirements-completed: [HYG-04, HYG-06]

coverage:
  - id: D1
    description: "CI receipt tracer delta in .github/workflows/ci.yml (sole product write)"
    requirement: "HYG-05"
    verification:
      - kind: other
        ref: "actionlint -no-color -oneline .github/workflows/ci.yml"
        status: pass
      - kind: other
        ref: "Plan 48-02 Task 1 <automated> commands (5/5 exit 0) + baseline comparison"
        status: pass
      - kind: other
        ref: "yaml.safe_load + compile of 6 inline python heredocs + STAGES/step-id match"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real Python 3.12/3.13/3.14 union on the final candidate plus matching-head hosted 9 matrix jobs + docs job"
    requirement: "HYG-05"
    verification: []
    human_judgment: true
    rationale: "Requires all product writers stopped, Phase 46 security and pre-push secrets acceptance, an authorized nonforce prior-branch push, and hosted Actions evidence for that exact head; none exists yet."

duration: 25min
completed: 2026-10-07
status: complete
---

# Phase 48 Plan 02: CI receipt tracer Summary

**The existing CI matrix now records interpreter, install, import, guard and per-stage exit evidence without changing any gate, matrix value, trigger or dependency. Phase 48 acceptance still needs real three-lane and hosted evidence.**

## Performance

- **Duration:** about 25 min (baseline to summary)
- **Started:** 2026-10-07T15:23:14Z (Task 0 baseline capture)
- **Completed:** 2026-10-07T15:48:06Z
- **Tasks:** 3 (Task 0 Main, Task 1 A11, Task 2 Main)
- **Files modified:** 1 product file; 2 Main planning artifacts

## Accomplishments

- Task 0 (Main): froze the pre-dispatch baseline `48-02-BASELINE.md` (SHA-256 `e223a4e53ce12bad04e0ea768c227c7351a80ee70d6c7a84bdaf435e7695e45d`, 76 porcelain entries, five bounded-path hashes, live peer declarations, provenance records) before the writer was released.
- Task 1 (A11, pool `OmegaPhase48CIReceipts`, worker `OmegaPhase48CIReceipts-1`, batch `OmegaPhase48CIReceipts-1-b1`): applied the approved receipt delta to `.github/workflows/ci.yml` only (68 → 528 lines). The worker ran no checks, Git or network operations.
- Task 2 (Main): ran every Task 1 `<automated>` command, the baseline comparison and static checks, and ingested the result. `Tutmu-p48-ci-receipts` moved IN_PROGRESS → IN_REVIEW; its review and quality gates are still missing.

## Task Commits

None yet. Main makes explicit-path commits after all product writers stop and the union runs. This follows the user's ownership decision, not the default per-task GSD commit protocol.

## Files Created/Modified

- `.github/workflows/ci.yml`: SHA-256 `a69d7f0d…4e63` → `122cc38f509a63fd108159af51ba49a42755762c053bb03208d79a6bd56fefea`. Changes:
  - `fail-fast: false` on verify, lint and types.
  - `python3 -m pip` installs with the original inputs.
  - Identity, pip version, `pip list --format=json` and `pip check` steps.
  - Verify-only ordinary imports of `discord` and `omega_prime.tools.discord`.
  - The suite runs with `-rA --junitxml=$RUNNER_TEMP/phase48-suite.xml`.
  - Every command step is wrapped to record and propagate its exit code.
  - An always-run `receipt summary` step in each matrix job.
  - The docs job is byte-identical.
- `.planning/phases/48-deps-matrix/48-02-BASELINE.md`: Main Task 0 artifact, frozen.

## Post-return verification (Main)

| Command | Exit | Observed |
|---|---|---|
| `git diff --stat -- .github/workflows/ci.yml` | 0 | `1 file changed, 469 insertions(+), 9 deletions(-)` |
| `git status --porcelain=v1 -uall` | 0 | 78 entries. Versus the 76-entry baseline, added: ` M .github/workflows/ci.yml` (A11 actual `changed_files`) and `?? …/48-02-BASELINE.md` (Main Task 0, baseline §d). Removed: none. Unexplained: none. |
| `sha256sum pyproject.toml requirements-lock.txt omega_prime/tests/test_deps_matrix.py omega_prime/tools/discord.py` | 0 | All four equal the baseline: `ea4763a7…a4d8`, `9c285986…b575`, `9d784f92…545c`, `fdc18221…ffddb` |
| `test "$(… grep -c 'fail-fast: false')" -eq 3` | 0 | added-line count 3 |
| `test "$(… grep -c 'python3 -m pip')" -gt 0` | 0 | added-line count 12 |

The mtime check found exactly two porcelain paths written at or after the capture: `ci.yml` at 15:40:21Z and the baseline itself.

Static checks:
- `actionlint -no-color -oneline` exited 0 with no findings; shellcheck integration was available.
- `yaml.safe_load` succeeded. It shows triggers push and pull_request; verify, lint and types each have matrix 3.12/3.13/3.14 with `fail-fast: false`; docs is unchanged.
- All 6 inline Python heredocs compile.
- Each job's `STAGES` list equals its step ids.

Execute-phase gates:
- Post-merge build gate exited 0. The language-sniffed `py_compile` picked 20 files from the read-only `oh-my-pi/` clone; it ran with `PYTHONPYCACHEPREFIX` outside the repo, so it gives no Omega Prime signal.
- Post-merge test gate: `python -m pytest -x -q --tb=short` passed 344 tests with 12 warnings and exit 0. This is the local `.venv` Python 3.12.3 run on the current dirty candidate only.
- `execute:wave:post` gates `verify.schema-drift`, `verify.codebase-drift` and `ui.safety-gate` all returned `block: false`.

## Edge-Probe Disposition (local://omega-phase48-edge-probe.json, all rows unresolved)

| # | Requirement | Category | Disposition | Reason |
|---|---|---|---|---|
| 1 | HYG-04 | adjacency | flagged assumption | Floors/lock byte-identical; no boundary-merge semantics in a receipt-only delta. |
| 2 | HYG-04 | empty | flagged assumption | No empty/null dependency-input path introduced; install inputs unchanged. |
| 3 | HYG-04 | ordering | flagged assumption | No ordering/stability semantics; lock snapshot order untouched. |
| 4 | HYG-04 | concurrency | backstop truth | Failed install leaves dependents not_run, never passed (summary mapping); runtime confirmation pending hosted run. |
| 5 | HYG-05 | adjacency | backstop truth | `fail-fast: false` on all three matrices; sibling-evidence behavior confirmable only by the hosted run. |
| 6 | HYG-05 | empty | backstop truth | Every matrix job installs before gating; same not_run mapping. |
| 7 | HYG-05 | ordering | flagged assumption | Matrix lanes independent; no cross-lane ordering claimed. |
| 8 | HYG-05 | concurrency | flagged assumption | Interrupt/parallel-runner guarantees belong to Actions plus Main's raw status/conclusion retention. |
| 9 | HYG-06 | concurrency | flagged assumption | MCP cap untouched; no concurrent-install semantics changed. |

## Threat Register (ASVS 1, block on high)

| ID | Disposition | Source status |
|---|---|---|
| T-48-02-01 Tampering (receipt steps) | mitigate | Capture-and-propagate only. No `continue-on-error`, no `|| true`, no unconditional success. Raw outcome/conclusion/job status are kept; exit is null only when unobserved. |
| T-48-02-02 Information disclosure (logs) | mitigate | Only allowlisted identity and GitHub/runner fields. `pip list` JSON has no URLs. The steps reference no secrets and dump no environment. |
| T-48-02-03 Denial of service (lost lane evidence) | mitigate | `fail-fast: false` ×3. |
| T-48-02-SC Supply chain | mitigate | No new packages, pins or install inputs. |

Out-of-delta findings reported by A11, both pre-existing and minor; routing belongs to A10/A14:
- DF-P48-01: Actions are pinned to mutable major tags (`@v4`/`@v5`).
- DF-P48-02: `ci.yml` declares no `permissions:` block.

## Artifacts and Symbols

- `.github/workflows/ci.yml`:
  - Jobs: `verify`, `lint`, `types`, `docs`.
  - Matrix step ids: `checkout`, `setup_python`, `interpreter_identity`, `pip_identity`, `install`, `resolved_distributions`, `pip_check`.
  - Verify-only ids: `discord_library_import`, `discord_product_import`, `suite`, `evals`, `assembly`.
  - Lint ids: `ruff`, `ruff_format`. Types id: `mypy`.
  - Every matrix job ends with an always-run `receipt summary` step that has `STAGES`.
- `.planning/phases/48-deps-matrix/48-02-BASELINE.md` (Main).

## D-ID Coverage

| Decision | Covered by |
|---|---|
| D-ctx1: real 3.12/3.13/3.14 plus matching-head hosted evidence, no waiver | Receipts delivered; acceptance pending (D2) |
| D-ctx2: gap plan only; preserve 48-01, floors, lock, MCP, guard and the 3.11 floor | Invariant hashes unchanged; 48-01 untouched |
| D-ctx3: sole A11 CI writer after plan/checker gate | Pool provenance and the scope comparison |
| D-ctx4: five-state receipts; missing, failed, skipped, cancelled or unexecuted stages never pass | `receipt summary` mapping |
| D-ctx5: diagnostics are smoke only | Flagged below |
| D-ctx6: final union after writers stop, candidate- and hosted-bound | Pending Main |
| D-ctx7: nonforce prior-branch push precedes hosted proof | Pending Main; no hosted-before-push circularity |

## Deviations from Plan

1. **Executor binding:** the user/A01 ownership route bound the product slot to the existing signed A11 record in a named specialized pool instead of a `gsd-executor` agent.
2. **Commits deferred:** commits wait for Main's explicit-path commits after the union, so the per-task commit spot-check has no commits yet.
3. **Hook query validation:** the dotted first-party gate queries fail the literal `loop-hook-dispatch` regex. They contain no shell metacharacters, and Main ran them as argv with no shell, which removes the injection risk the regex guards against. Results are recorded above.

## Flagged Assumptions / Pending Main

- The `local://omega-p48-real-runtime-diagnostics.json` diagnostics (3.13.14/3.14.6) are dirty-tree smoke, not acceptance.
- Pending Main work, in order:
  1. The stopped-writer real 3-lane union (identity, install, imports, suite with the named guard testcase, evals, assembly, Ruff, mypy, pip check).
  2. Phase 46 security and pre-push secrets acceptance.
  3. A nonforce push of the prior branch.
  4. Collection of the hosted 9 matrix jobs plus docs for that exact head.
- Edge rows 1, 2, 3, 7, 8 and 9 stay unresolved as flagged assumptions.
- Unavailable evidence stays null-exit, never simulated.

## Self-Check: PASSED

Scope and static checks only; this is not runtime or hosted acceptance.

---
*Phase: 48-deps-matrix*
*Completed: 2026-10-07*

## Native GSD continuation — 2026-10-07

The user authorized native GSD agents in place of the unavailable signed
controller. Historical signed records above remain unchanged; they do not
certify this continuation.

- `P48ReceiptDedup` addressed the existing WR-01/IN-01 findings in
  `.github/workflows/ci.yml` and the new stdlib-only
  `omega_prime/scripts/ci_receipt.py`. The workflow is now 169 lines; identity,
  command exit recording, and receipt summaries share the helper.
- Main ran `actionlint -no-color -oneline .github/workflows/ci.yml`: exit 0.
- Main ran Ruff lint on the helper: exit 0. The format check reported one
  file needing formatting; Main applied Ruff formatting successfully.
- Main exercised 14 actual helper subprocess scenarios using temporary
  output/JUnit fixtures: successful command; exit 3; missing executable
  (127); signal termination (143); matching and mismatched real interpreter;
  passed, failed-prerequisite, cancelled, and missing-stage summaries;
  missing JUnit; and failed, skipped, and passed named Discord guard.
  All expected exits, receipt output files, and stage/guard state assertions
  held. Temporary fixtures were removed.
- Evidence: `local://phase48-ci-smoke.json` in the native continuation
  session. Independent `P48HelperReview` passed source review with no
  material findings and closed WR-01/IN-01. Main's current LSP diagnostics
  for the helper returned OK. No signed swarm verdict was issued or changed.

These are CI-helper smoke results, not HYG-05 completion. Fresh final-candidate
three-interpreter union, Phase 46 security evidence, nonforce publication, and
matching-head hosted CI remain required. No commit or push was performed.
