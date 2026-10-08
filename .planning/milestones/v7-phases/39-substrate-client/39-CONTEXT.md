# Phase 39: Substrate client - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Omega Prime speaks substrate-mcp: brief, events, shared memory (SUB-01, SUB-02).
Ground truth: `~/src/repos/agent-substrate/packages/mcp-server/src/`
(`server.ts` routes, `mcp.ts` tools, `types.ts` kinds/surfaces), the
grokbot-production-loop doc (brief-on-open, substrate-only, fail-open),
and the local `HttpTransport` + `CredentialBroker` the client must reuse.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Locked by v7 milestone decisions (2026-10-03): substrate-mediated direction,
shared `ultrathink` Hindsight bank (Phase 40), fakes + opt-in live probes
(Phase 43). Omega Prime is the `grok-bot` surface (substrate has no `omega_prime` surface;
adding one is an upstream change, out of scope).

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
