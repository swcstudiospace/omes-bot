# Roadmap: Omega Prime

## Milestones

- ✅ **v1 One Omega Prime agent** — Phases 1-12 (shipped 2026-10-03)
- ✅ **v2 Enterprise hardening** — Phases 13-16 (shipped 2026-10-03)
- ✅ **v3 Grok Bot** — Phases 17-20 (shipped 2026-10-03)
- ✅ **v4 Third-party integrations** — Phases 21-25 (shipped 2026-10-03)
- ✅ **v5 Desk packs** — Phases 26-33 (shipped 2026-10-03)
- ✅ **v6 Grok ship** — Phases 34-38 (shipped 2026-10-03)
- ✅ **v7 Substrate surface** — Phases 39-43 (shipped 2026-10-03)
- ✅ **v8 Public launch** — Phases 44-45 (shipped 2026-10-03)
- ✅ **v9 SOTA upgrade** — Phases 46-52 (shipped 2026-10-08)
- ⏳ **v10 Prime merge** — Phases 53-60 (in progress)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v9-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v9-phases/`.

## Phases

**Active milestone: v10 Prime merge** (see `milestones/v10-ROADMAP.md`)

- [x] **Phase 53: Prime discovery + parity baseline** - Capability map + overlap map; cargo baseline green; VENDOR pin.
- [x] **Phase 54: Rust workspace CI integration** - Parity-oracle CI job; cargo-deny; toolchain pin.
- [x] **Phase 55: RLM recursion port** - spawn/collect/list/delete/create_session/progress_note into the loop.
- [x] **Phase 56: Continual harness port** - /refine, harness state, snapshots, rollback.
- [x] **Phase 57: Agent loop upgrade** - Goals, heartbeats, autonomous mode, agent messaging; config flags; degraded mode; regression parity.
- [ ] **Phase 58: Connector layer + parity suite** - Typed adapters, contract tests, failure injection, parity fixtures.
- [ ] **Phase 59: Repository hardening** - AGPL-3.0, root files, docs, supply-chain CI.
- [ ] **Phase 60: Milestone audit + closeout** - Audit, archive, cleanup.

## Phase Details

### Phase 53: Prime discovery + parity baseline
**Goal**: Every Prime capability to be ported is mapped to a source module with must-preserve behaviors cited and an Omega Prime merge target; the Rust workspace's own test suite passes as the parity baseline; the upstream pin is recorded.
**Depends on**: v9 complete
**Requirements**: DISC-01, DISC-02, DISC-03
**Plans**: 1 plan

Plans:
- [x] 53-01: Capability map + overlap map + Rust baseline

### Phase 54: Rust workspace CI integration
**Goal**: CI keeps the parity oracle green on every change: the prime-agent workspace builds and tests on a pinned toolchain with locked dependencies, cargo-deny enforces the license allowlist, and builds are cached.
**Depends on**: 53
**Requirements**: BUILD-01, BUILD-02, BUILD-03
**Plans**: 1 plan

Plans:
- [x] 54-01: Parity-oracle CI job + toolchain pin + deny gate

### Phase 55: RLM recursion port
**Goal**: The agent spawns child agents mid-turn with Prime's RLM semantics — spawn/collect/list/delete/create_session/progress_note — as rostered tools on top of the existing delegate machinery, with persistent working context across calls.
**Depends on**: 53
**Requirements**: RLM-01, RLM-02, RLM-03, RLM-04
**Plans**: 1 plan

Plans:
- [x] 55-01: RLM recursion tools + semantics port

### Phase 56: Continual harness port
**Goal**: `/refine` reviews the current trajectory and applies small, evidence-backed updates to supplemental harness state with recorded snapshots and rollback; the immutable base system prompt is never rewritten.
**Depends on**: 55
**Requirements**: HARN-01, HARN-02, HARN-03, HARN-04
**Plans**: 1 plan

Plans:
- [x] 56-01: Harness state + refine loop + snapshots

### Phase 57: Agent loop upgrade
**Goal**: Goals, heartbeats, autonomous mode (budgets + quality gates), and agent-to-agent messaging run inside the one conversation loop; every Prime family is individually config-gated (default off); failures degrade with loud structured warnings; with Prime disabled the Hermes+Omp loop behaves exactly as before.
**Depends on**: 56
**Requirements**: LOOP-01, LOOP-02, LOOP-03, LOOP-04, LOOP-05, LOOP-06, LOOP-07
**Plans**: 2 plans

Plans:
- [x] 57-01: Goals + heartbeats + autonomous mode
- [x] 57-02: Agent messaging + config flags + degraded mode + regression

### Phase 58: Connector layer + parity suite
**Goal**: The ported Prime capabilities sit behind typed Python adapter modules with versioned contracts; contract tests cover both sides; failure-injection proves the loop survives capability panic/error/timeout; behavior-parity fixtures generated from the Rust baseline pin the port's fidelity.
**Depends on**: 57
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04
**Plans**: 1 plan

Plans:
- [ ] 58-01: Typed connectors + contract/failure-injection/parity tests

### Phase 59: Repository hardening
**Goal**: The repo reads as a state-of-the-art, enterprise-grade open-source project: AGPL-3.0 LICENSE with "Copyright (C) 2026 Spectrum Web Co", the full root file set, a rewritten README with the three-source architecture, merge documentation, and supply-chain CI on both ecosystems.
**Depends on**: 58
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, REPO-05
**Plans**: 2 plans

Plans:
- [ ] 59-01: License + root files + community automation
- [ ] 59-02: README + docs + supply-chain CI

### Phase 60: Milestone audit + closeout
**Goal**: The milestone audit verifies every requirement with cited evidence; v10 phase dirs archive to `milestones/v10-phases/`; ROADMAP collapses; STATE records completion; cleanup runs per convention.
**Depends on**: 59
**Requirements**: DONE-01, DONE-02
**Plans**: 1 plan

Plans:
- [ ] 60-01: Audit + archive + cleanup
