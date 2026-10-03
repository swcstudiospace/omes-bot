# Requirements: v6 Grok ship

Milestone-scoped. v5 requirements are archived in `milestones/v5-REQUIREMENTS.md`.
Ground truth: `.planning/research/v6-runtime-spike.md`. User decisions (2026-10-03):
hybrid architecture (Add-Bot template + optional Omes MCP tool host), MIT license
(bridge-only ultrathink integration, no AGPL vendoring).

## Magic keywords

- [x] **KEY-01**: `ultrathink`, `orchestrate`, `workflowz` recognized in prompts per Omp matching rules (lowercase standalone prose; code spans/blocks ignored; per-turn).
- [x] **KEY-02**: Each word injects its notice for the turn with requires-gates adapted to Omes tools (`orchestrate` needs `delegate_task`; `workflowz` needs `delegate_task` + subagent batching).

## Ultrathink native

- [x] **ULT-01**: Ultrathink Grok-host flow (plan → kickoff → ship) available as Omes skills/routines (prompt-native, no dependency).
- [x] **ULT-02**: Bridge tools to the `bun` ultrathink CLI (uplift/track/ship); no vendored AGPL code in this repo.

## MCP tool host

- [x] **MCP-01**: Omes tool registry served over MCP (stdio), roster-gated, with fake-backed tests.
- [x] **MCP-02**: OpenShell host profile + AgentOS host notes for running the tool host.

## Template + setup

- [ ] **TPL-01**: Polished Add-Bot template + setup flow (install → secrets → optional custom MCP → smoke prompt) with a verifiable smoke check.
- [ ] **TPL-02**: MIT LICENSE file at repo root.

## Docs + GitBook

- [ ] **DOC-01**: Build-aesthetics documentation (how Omes is built: agent, packs, contracts, receipts).
- [ ] **DOC-02**: User guide + setup flow docs for Grok Bot installs.
- [ ] **DOC-03**: GitBook Git Sync structure (`docs/`, `SUMMARY.md`) + dashboard connection guide.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| KEY-01 | Phase 34 | Done |
| KEY-02 | Phase 34 | Done |
| ULT-01 | Phase 35 | Done |
| ULT-02 | Phase 35 | Done |
| MCP-01 | Phase 36 | Done |
| MCP-02 | Phase 36 | Done |
| TPL-01 | Phase 37 | Todo |
| TPL-02 | Phase 37 | Todo |
| DOC-01 | Phase 38 | Todo |
| DOC-02 | Phase 38 | Todo |
| DOC-03 | Phase 38 | Todo |

**Coverage:**

- v6 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v6 milestone)*
