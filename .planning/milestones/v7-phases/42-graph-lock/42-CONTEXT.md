# Phase 42: Graph + store lock - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Task coordination through substrate graph ops (claim/release/complete +
heartbeat) with lease handling, and a test-enforced ban on direct
GreptimeDB/TimescaleDB/DragonflyDB clients under `omega_prime/` (GRP-01, LOCK-01).
Ground truth: upstream `graph_claim`/`graph_release`/`graph_complete`/
`graph_heartbeat` (`mcp.ts`), the family `approvals` convention (x/lead),
and the existing injected `timescale`/`greptime` seams in
`omega_prime/tools/systems.py` (dependency inversion, no endpoints — the sanctioned
exception the lock test documents).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Locked by v7 milestone decisions (2026-10-03): substrate-mediated direction
(the lock test is its enforcement), shared bank, fakes + opt-in live probes
(Phase 43). `graph_handoff` stays out (upstream Phase 2 stub).

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
