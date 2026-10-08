# Phase 48: Dependencies + matrix - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Dependency floors rise to the verified versions with a committed lockfile;
CI runs the suite on Python 3.12–3.14 (floor stays 3.11); the Discord
import is guarded for 3.13+ (audioop removal); the MCP SDK pins to the v2
line with spec conformance recorded. No behavior changes beyond the import
guard's fail-soft path.

Out: provider behavior (Phases 49–50). Out: lint/type config (done).
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Lockfile format: plain `pip freeze` (no new
toolchain). Matrix scope: at minimum the verify job; extend to lint/types
if cheap. Discord guard shape follows the codebase's existing
not-configured conventions.


### Focused validation gap closure — resolved user decision
- Matrix 1 requires actual Python 3.12, 3.13, and 3.14 executions and matching-head hosted CI evidence. The original simulation receipt is historical, not acceptance; no waiver or deferral is authorized.
- Add focused gap-closure plans only. Preserve the completed 48-01 dependency, lockfile, MCP, and Discord-guard implementation; the Python floor stays 3.11.
- The accepted A11 preparation report is `agent://OmegaP48Preparation`; its report review and quality gates passed. Apply its minimal CI receipt delta through the sole `.github/workflows/ci.yml` writer after the focused GSD plan/checker gate. This disjoint CI preparation does not depend on the Phase 46 design rerun.
- Record actual interpreter identity, same-environment installation and pip checks, ordinary installed Discord imports, the named Discord guard, full-suite skips/outcomes, evals, assembly, Ruff format/check, and mypy. Missing, failed, skipped, cancelled, or unexecuted required stages cannot pass.
- Main exercised real CPython 3.13.14 and 3.14.6 diagnostics: installed Discord and product imports, the named missing-library guard, and interpreter-bound `pip check` all exited 0. Receipt: `local://omega-p48-real-runtime-diagnostics.json`. These pre-implementation dirty-worktree diagnostics are not final full-suite, exact-candidate, clean-install, or hosted CI proof.
- Run final union verification after product writers stop. Link local receipts to the actual tested candidate and hosted receipts to its checkout SHA, run attempt, job, interpreter, and actual stage exits.
- The verified prior-branch nonforce push precedes hosted push-triggered CI evidence and Omega implementation. Phase 46 runtime security and pre-push secret checks remain prerequisites for publication; no main merge or Railway deployment is authorized by this plan.
- On resume, the user authorized native GSD agents in place of the unavailable signed swarm controller. Retain all real-interpreter and matching-head CI gates, preserve the historical signed receipts, and leave the old `.swarm/` ledger unchanged. The sole CI writer may address the existing `48-REVIEW.md` duplication finding without changing job matrices, triggers, dependency floors, or failure propagation.
</decisions>

<code_context>
## Existing Code Insights

Historical initial-planning snapshot (superseded by the actual interpreter
availability and pending acceptance decisions above):

Installed versions are current (tweepy 4.17, mcp 2.3.0, pyrit 1.1.0,
aiogram 3.31, discord.py 2.7.1, playwright 1.63, APScheduler 3.11.3,
Appium 6.0.7 — re-verify before pinning). Only Python 3.12 is local;
3.13/3.14 coverage comes from CI plus a simulated-import-error test.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (HYG-04, HYG-05, HYG-06).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
