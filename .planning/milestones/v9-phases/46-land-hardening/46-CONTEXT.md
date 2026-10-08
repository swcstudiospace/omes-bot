# Phase 46: Land in-flight hardening - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

The working tree carries 24 uncommitted files of hardening work that predate
v9 (recursive redaction, intake lease reclaim/release, tool write-path
hardening, skill/routine/doc touch-ups, and their tests). This phase reviews
every hunk, verifies the gates, fixes any issues found, and commits the code
so later v9 phases build on a clean tree.

Out: the `.planning/` edits from v9 milestone setup (they stay uncommitted
per `commit_docs=false`). Out: any new v9 behavior — this phase lands what
exists, nothing more.
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Use ROADMAP phase goal, success criteria, and
codebase conventions to guide decisions. Review standard: each hunk must
match existing contracts (error shapes, approval kinds, roster/policy
composition) and carry a test where behavior changed.

### Focused Gap Closure — resolved user decisions
- **D-01:** Security 1 means remediate both T-46-08 and T-46-12. No high-risk waiver or acceptance is authorized.
- **D-02:** Matrix 1 means real Python 3.12/3.13/3.14 runtime and matching-head CI evidence. A declared matrix, simulated version or historical receipt is not acceptance.
- **D-03:** Preserve the completed 46-01 landing and original dirty Phase52 work. Add focused `gap_closure: true` plans; execute only those plans, never replay historical work.
- **D-04:** Close the fetch gap with all-address destination validation, exact endpoint policy, actual-peer pinning/checks and original HTTPS hostname verification. Close the browser gap for every request with real mandatory egress enforcement; neither an initial probe nor route filtering alone is sufficient. Preserve functional allowed browsing and the existing public result contracts.
- **D-05:** The parent owns union checks, runtime smoke, explicit-path commits and nonforce prior-branch publication. Child implementation slices must not run checks, gates or Git operations mid-flight.
- **D-06:** Push the verified prior branch before the Omega rename. Final Omega merge remains review-gated; Railway is connect/prepare only; milestone audit/archive is authorized only after actual security, matrix and audit gates pass.
- **D-07:** On resume, the user explicitly selected **Use native GSD agents** because the signed swarm controller is unavailable. Native GSD planning, execution, and independent review replace signed dispatch for this continuation. Preserve every security, real-runtime, review, and CI acceptance requirement; leave `.swarm/` records unchanged and never fabricate signatures or verdicts. Existing rejected design reports remain required review inputs, not accepted contracts.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research: read the full
diff of the 24 files plus the composition tests (roster/policy/template)
they touch.

</code_context>
<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (LAND-01, LAND-02).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
