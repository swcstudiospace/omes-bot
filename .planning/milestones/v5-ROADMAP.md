# Roadmap: Omes Bot v5

## Overview

v4 wired third-party libraries (see `milestones/v4-ROADMAP.md`). v5 absorbs
the entire Programming Desk into Omes as the Lead with domain packs: desk
seats become skill dirs + tool families + routines + roster entries in the
one Omes agent, and interactive browser/device review lands behind the
vision and browser transports. Numbering continues. A phase is done when
its parity checks pass.

## Phases

- [x] **Phase 26: Lead pack** - Intake/dispatch routines + core/lead tools.
- [x] **Phase 27: Systems pack** - Backend tools + Rust/Python skills.
- [x] **Phase 28: Web pack** - Vercel/preview tools + Playwright vision review.
- [x] **Phase 29: Mobile pack** - Store tools + interactive device review.
- [x] **Phase 30: Infra pack** - Railway/Tailscale/VPS/DB tools + skills.
- [x] **Phase 31: Quality pack** - Gates, Greptile, receipts, security tools.
- [x] **Phase 32: Packs + skills remainder** - App packs, skills, prompts, contracts. (completed 2026-10-03)
- [x] **Phase 33: Hardening** - Pack evals, receipts E2E, docs. (completed 2026-10-03)

## Phase Details

### Phase 26: Lead pack

**Goal**: Omes works like the desk Lead: intake in, tickets out, dispatched and consolidated.
**Depends on**: v4 complete
**Requirements**: LEAD-01, LEAD-02, LEAD-03
**Success Criteria** (what must be TRUE):

  1. An intake routine produces tickets, dispatches through delegate/todo, and consolidates receipts into a report.
  2. Core+lead desk tools are registry families with roster/policy entries and fake-backed tests.
  3. Memory and receipt checks reuse Omes memory/receipts (no parallel stores).

**Plans**: 2 plans

Plans:

- [x] 26-01: Lead core/lead tool families
- [x] 26-02: Lead routine, skill, evals

### Phase 27: Systems pack

**Goal**: Backend seat capability as an Omes pack.
**Depends on**: Phase 26
**Requirements**: SYS-01, SYS-02
**Success Criteria** (what must be TRUE):

  1. Systems tools are a registry family with roster/policy entries and fake-backed tests.
  2. Rust and Python platform skills exist and the template can name them.

**Plans**: 1 plan

Plans:

- [x] 27-01: Systems tools and skills

### Phase 28: Web pack

**Goal**: Web seat capability plus real rendered review.
**Depends on**: Phase 27
**Requirements**: WEB-01, WEB-02, WEB-03
**Success Criteria** (what must be TRUE):

  1. Web tools are a registry family with roster/policy entries and fake-backed tests.
  2. A Playwright transport drives navigate/screenshot; screenshots reach vision_analyze; connectivity checks report status/latency.
  3. TypeScript/Deno and Vercel skills exist and the template can name them.

**Plans**: 1 plan

Plans:

- [x] 28-01: Web tools, skills, and browser vision transport

### Phase 29: Mobile pack

**Goal**: Mobile seats capability plus interactive device review.
**Depends on**: Phase 28
**Requirements**: MOB-01, MOB-02, MOB-03
**Success Criteria** (what must be TRUE):

  1. Store tools are a registry family with roster/policy entries and fake-backed tests.
  2. Device transports (Appium/adb/simctl seams) capture screenshots for vision review; tests use fakes only.
  3. Android and iOS skills exist and the template can name them.

**Plans**: 1 plan

Plans:

- [x] 29-01: Mobile tools, skills, and device transports

### Phase 30: Infra pack

**Goal**: Infra seat capability as an Omes pack.
**Depends on**: Phase 29
**Requirements**: INF-01, INF-02
**Success Criteria** (what must be TRUE):

  1. Infra tools are a registry family with roster/policy entries and fake-backed tests.
  2. Railway/Tailscale, Terraform/K8s, and remote-dev-machine skills exist and the template can name them.

**Plans**: 1 plan

Plans:

- [x] 30-01: Infra tools and skills

### Phase 31: Quality pack

**Goal**: Quality seat capability as an Omes pack; desk gates mirrored.
**Depends on**: Phase 30
**Requirements**: QUA-01, QUA-02, QUA-03
**Success Criteria** (what must be TRUE):

  1. Quality tools are a registry family with roster/policy entries and fake-backed tests.
  2. Desk CI gates are mirrored as Omes eval cases and CI checks.
  3. Code-review, debugging, and security skills exist and the template can name them.

**Plans**: 1 plan

Plans:

- [x] 31-01: Quality tools, skills, and gate mirrors

### Phase 32: Packs + skills remainder

**Goal**: Everything else in the desk lands in Omes.
**Depends on**: Phase 31
**Requirements**: REM-01, REM-02, REM-03
**Success Criteria** (what must be TRUE):

  1. App tool-pack tools are a registry family with roster/policy entries and fake-backed tests.
  2. All remaining desk skills exist in `omes/skills/`.
  3. Seat prompts, templates, roster JSON, ownership, and contract versions are merged into Omes contracts.

**Plans**: 1 plan

Plans:

- [x] 32-01: Remaining packs, skills, prompts, contracts

### Phase 33: Hardening

**Goal**: The absorbed desk is guarded and documented.
**Depends on**: Phase 32
**Requirements**: HRD-01, HRD-02
**Success Criteria** (what must be TRUE):

  1. Per-pack eval cases assert behaviour and refusals deterministically.
  2. A receipts E2E proves claims cite commands + exit codes with no self-approval.

**Plans**: 1 plan

Plans:

- [x] 33-01: Pack evals, receipts E2E, docs

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 26. Lead pack | 2/2 | Complete | 2026-10-03 |
| 27. Systems pack | 1/1 | Complete | 2026-10-03 |
| 28. Web pack | 1/1 | Complete | 2026-10-03 |
| 29. Mobile pack | 1/1 | Complete | 2026-10-03 |
| 30. Infra pack | 1/1 | Complete    | 2026-10-03 |
| 31. Quality pack | 1/1 | Complete | 2026-10-03 |
| 32. Packs + skills remainder | 1/1 | Complete    | 2026-10-03 |
| 33. Hardening | 1/1 | Complete    | 2026-10-03 |
