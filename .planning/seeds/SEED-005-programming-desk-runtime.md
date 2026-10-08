---
id: SEED-005
status: dormant
planted: 2026-10-07
planted_during: v9 SOTA-upgrade phase 46/48 gap closure
trigger_when: when planning the Omega milestone (v10) after v9 closure and the verified prior-branch push
scope: Large
---

# SEED-005: Programming Desk logic as the native 1-Bot Programmer runtime

## Why This Matters

v5 ported 49/50 desk tool surfaces and all 24 skills, but the runtime is unconfigured: desk contexts are built with empty seams, coding tools root at <root>/omega_prime so Omega cannot program a target repo, delegate_task is not served, the lead pass routine is test-only, gates only run Omega Prime's own suite, receipts are model-written and bot-00-omega-prime cannot approve its own receipts, and Railway/Greptile/Vercel/Play/ASC clients do not exist.

## When to Surface

**Trigger:** when planning the Omega milestone (v10) after v9 closure and the verified prior-branch push.

This seed will surface during `/gsd:new-milestone` when the milestone scope matches.

## Scope Estimate

**Large** — estimated from the read-only research recorded in the breadcrumbs.

## Breadcrumbs

- `omega_prime/mcp_server.py:115-188`
- `omega_prime/tools/lead.py`
- `omega_prime/routines/desk_lead.py`
- `omega_prime/tools/quality.py`
- `omega_prime/tools/infra.py`
- `/root/.omp/agent/sessions/-src-repos-Omes-Bot/2026-10-07T08-07-02-266Z_01a11566-d17a-71fc-9303-d0456a5234f3/local/omega-research-ScoutDesk.json`

## Notes

Captured from the user's orchestration request in this session. The user's integration decisions are recorded in `/root/.omp/agent/sessions/-src-repos-Omes-Bot/2026-10-07T08-07-02-266Z_01a11566-d17a-71fc-9303-d0456a5234f3/local/omega-integration-decisions.json`. Research is source-only, not runtime proof.
