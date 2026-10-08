# Phase 51: Red-team depth - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

No test writes outside the repo/tmp (PyRIT home-dir writes isolated; the
suite collects clean in sandboxes without HOME redirection). PyRIT
orchestrator-driven multi-turn attacks and scorer-based judging run with a
deterministic keyless subset in CI. PyRIT memory stays in-memory or
file-isolated per test.

Out: live/keyed red-teaming in CI (manual opt-in), new attack batteries
beyond the depth harness (Phase 52 grows cases).
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Isolation mechanism (env redirection vs fixture),
orchestrator choice, and scorer choice follow the installed PyRIT 1.1.0
API and stay deterministic without keys.

</decisions>

<code_context>
## Existing Code Insights

`pyrit_target.py` wraps the registry as a PyRIT target with a deterministic
attack battery. PyRIT writes DuckDB/memory logs under `~/.local/share` at
import/first-use, which breaks sandboxed collection today.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (DPT-01, DPT-02, DPT-03).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
