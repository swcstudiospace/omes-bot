# Roadmap: Omes Bot

## Milestones

- ✅ **v1 One Omes agent** — Phases 1-12 (shipped 2026-10-03)
- ✅ **v2 Enterprise hardening** — Phases 13-16 (shipped 2026-10-03)
- ✅ **v3 Grok Bot** — Phases 17-20 (shipped 2026-10-03)
- ✅ **v4 Third-party integrations** — Phases 21-25 (shipped 2026-10-03)
- ✅ **v5 Desk packs** — Phases 26-33 (shipped 2026-10-03)
- 🚧 **v6 Grok ship** — Phases 34-38 (in progress)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v5-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v5-phases/`.

## v6 Overview

v5 absorbed the desk (see `milestones/v5-ROADMAP.md`). v6 ships Omes
as a Grok Bot Add-Bot product: magic keywords ported from Omp,
ultrathink natively integrated (prompt routines + CLI bridge, no
AGPL vendoring), an MCP tool host for installs that want real Omes
tools, a clean template + setup flow, and docs structured for
GitBook Git Sync. Numbering continues. A phase is done when its
parity checks pass.

## Phases

- [x] **Phase 34: Magic keywords** - ultrathink/orchestrate/workflowz in the Omes loop. (completed 2026-10-03)
- [x] **Phase 35: Ultrathink native** - Grok-host routines + CLI bridge tools. (completed 2026-10-03)
- [ ] **Phase 36: MCP tool host** - Registry over MCP stdio + host profiles.
- [ ] **Phase 37: Template + setup** - Add-Bot template, setup flow, MIT license.
- [ ] **Phase 38: Docs + GitBook** - Aesthetics, user guide, sync structure.

## Phase Details

### Phase 34: Magic keywords

**Goal**: Omp's three magic words work in Omes prompts.
**Depends on**: v5 complete
**Requirements**: KEY-01, KEY-02
**Success Criteria** (what must be TRUE):

  1. The three words are recognized per Omp matching rules with fake-backed tests.
  2. Each word injects its adapted notice for the turn, gated on its required tools.

Plans:

- [x] 34-01: Keyword matcher, notices, loop injection

### Phase 35: Ultrathink native

**Goal**: Ultrathink plan/track/ship flows run natively in Omes Bot.
**Depends on**: Phase 34
**Requirements**: ULT-01, ULT-02
**Success Criteria** (what must be TRUE):

  1. Ultrathink Grok-host flow exists as Omes skills/routines with no new dependency.
  2. Bridge tools invoke the bun ultrathink CLI behind injected runners with fake-backed tests, and no AGPL source is vendored.

Plans:

- [x] 35-01: Ultrathink skills, routines, bridge tools

### Phase 36: MCP tool host

**Goal**: Installs can attach real Omes tools over MCP.
**Depends on**: Phase 35
**Requirements**: MCP-01, MCP-02
**Success Criteria** (what must be TRUE):

  1. The registry serves over MCP stdio, roster-gated, with fake-backed tests.
  2. An OpenShell profile and AgentOS host notes exist for running the host.

Plans:

- [ ] 36-01: MCP server, profiles, host notes

### Phase 37: Template + setup

**Goal**: A clean Add-Bot product with a verifiable setup flow.
**Depends on**: Phase 36
**Requirements**: TPL-01, TPL-02
**Success Criteria** (what must be TRUE):

  1. The template + setup flow (install → secrets → optional MCP → smoke) is documented and the smoke check passes.
  2. MIT LICENSE exists at the repo root.

Plans:

- [ ] 37-01: Template polish, setup flow, license

### Phase 38: Docs + GitBook

**Goal**: Omes is documented for builders and users, ready for GitBook sync.
**Depends on**: Phase 37
**Requirements**: DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):

  1. Build-aesthetics, user guide, and setup flow docs exist under `docs/`.
  2. `SUMMARY.md` + sync config exist with a dashboard connection guide.

Plans:

- [ ] 38-01: Docs set, summary, sync guide

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 34. Magic keywords | 1/1 | Complete    | 2026-10-03 |
| 35. Ultrathink native | 1/1 | Complete    | 2026-10-03 |
| 36. MCP tool host | 0/1 | Not started | — |
| 37. Template + setup | 0/1 | Not started | — |
| 38. Docs + GitBook | 0/1 | Not started | — |
