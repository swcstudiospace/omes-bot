# Phase 41: Loop wiring + docs - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

The loop lives on the substrate: brief-on-open injected into the system
prompt, turn/tool/file/session events with surface + graph_id provenance,
and a `substrate_docs_search` tool answering from RAGflow via substrate MCP
(SUB-03, RAG-01). Ground truth: `omega_prime/agent/conversation_loop.py` +
`turn_tool_round.py` seams, the `register_*_tools` family pattern with the
roster-exactness test, and upstream `docs_search` (`mcp.ts`).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Locked by v7 milestone decisions (2026-10-03): substrate-mediated direction,
shared `ultrathink` bank, fakes + opt-in live probes (Phase 43). Tool args
never leave the process in event summaries (PD-4).

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
