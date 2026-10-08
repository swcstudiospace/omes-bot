---
id: SEED-002
status: dormant
planted: 2026-10-07
planted_during: v9 SOTA-upgrade phase 46/48 gap closure
trigger_when: when planning the Omega milestone (v10) after v9 closure and the verified prior-branch push
scope: Medium
---

# SEED-002: Native Agent Substrate connectivity

## Why This Matters

Omes already has SubstrateClient, SubstrateSession, five substrate tools, HindsightService/Bridge and a store-lock test. Research shows the live connection is broken: MCP posts lack the Streamable HTTP Accept header and parse SSE as JSON (406 risk), memory_search shape mismatch, isError ignored, the session trail and Hindsight are only built in tests, and endpoints default to loopback. User decision: keep substrate mediation for Greptime/Timescale/Dragonfly.

## When to Surface

**Trigger:** when planning the Omega milestone (v10) after v9 closure and the verified prior-branch push.

This seed will surface during `/gsd:new-milestone` when the milestone scope matches.

## Scope Estimate

**Medium** — estimated from the read-only research recorded in the breadcrumbs.

## Breadcrumbs

- `omes/substrate/client.py`
- `omes/substrate/session.py`
- `omes/tools/substrate_tools.py`
- `omes/mcp_server.py:178-186`
- `/root/src/repos/agent-substrate/packages/mcp-server/src/server.ts`
- `/root/.omp/agent/sessions/-src-repos-Omes-Bot/2026-10-07T08-07-02-266Z_01a11566-d17a-71fc-9303-d0456a5234f3/local/omega-research-ScoutSubstrate.json`

## Notes

Captured from the user's orchestration request in this session. The user's integration decisions are recorded in `/root/.omp/agent/sessions/-src-repos-Omes-Bot/2026-10-07T08-07-02-266Z_01a11566-d17a-71fc-9303-d0456a5234f3/local/omega-integration-decisions.json`. Research is source-only, not runtime proof.
