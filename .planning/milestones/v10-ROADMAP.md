# Roadmap: Omega Prime v10 — Prime merge

**Defined:** 2026-10-08
**Status:** Active

## Overview

v9 brought the one-agent product to state-of-the-art engineering standards
(see `v9-ROADMAP.md`). v10 merges the third agent: Prime Agent
(`prime-agent/`, upstream github.com/PrimeIntellect-ai/prime-agent @
`967eb13f`, MIT) joins Hermes and Omp as a third logic source inside the
same one-Python-process Omega Prime agent. Prime's differentiating logic —
RLM subagent recursion, the continual harness, goals/heartbeats/autonomous
mode, and agent-to-agent messaging — is behavior-ported into `omega_prime/`
per the v1–v9 precedent. The Rust workspace stays in the tree as an
ignored, read-only upstream checkout and serves as the CI-built parity
oracle. The milestone ends with the repo relicensed AGPL-3.0 (Spectrum Web
Co 2026) and hardened to enterprise open-source standards. Numbering
continues from 52. A phase is done when its success criteria pass;
verification stays hermetic (live probes manual opt-in).

## Decisions (2026-10-08, recorded at milestone start)

1. **Architecture:** behavior port into Python. Prime Agent has no
   PyO3/maturin bindings — its Rust↔Python wiring is a spawned-kernel
   process boundary — and Omega Prime's standing rule is one Python
   process. The Rust workspace is built and tested in CI as the parity
   oracle; connectors are typed Python adapter modules exposing the ported
   capabilities through the registry/roster.
2. **Loop design:** capability merge into the single existing conversation
   loop. Hermes and Omp are already one merged loop; Prime joins as a
   third logic source (RLM spawn/collect extends delegate, /refine extends
   the curator, autonomous mode as a mode, heartbeats extend cron, agent
   messaging as tools).
3. **License:** GNU AGPL-3.0, "Copyright (C) 2026 Spectrum Web Co",
   SPDX-License-Identifier: AGPL-3.0-only headers on new source files.
   Ported Prime code retains MIT attribution per `VENDOR.md`. Supersedes
   the v6 MIT decision by explicit user request.
4. **Degradation:** degrade-with-warning. Prime capability modules are
   default-off config flags; when disabled or failed, the loop continues
   with a loud structured warning and Hermes+Omp behavior is preserved
   bit-for-bit.
5. **Leftover milestones:** none. v1–v9 verified complete; v10 starts on a
   green baseline (372 tests, 26 evals, all gates exit 0).

## Phases

- [x] **Phase 53: Prime discovery + parity baseline** - Capability map and overlap map land under `.planning/research/`; `cargo test --workspace` baseline green on the prime-agent checkout; upstream pin recorded in VENDOR.md.
- [x] **Phase 54: Rust workspace CI integration** - CI builds and tests the prime-agent workspace as the parity oracle (pinned toolchain, `--locked`); cargo-deny license gate scoped to that workspace; build caching.
- [x] **Phase 55: RLM recursion port** - `rlm.spawn`/`collect`/`list_subagents`/`delete_subagent`/`create_session`/`progress_note` and persistent-REPL semantics ported into `omega_prime` (extends `agent/delegate.py`); rostered tools; scripted-model tests.
- [x] **Phase 56: Continual harness port** - `/refine` refinement loop, harness state (supplemental prompts, memories, skill descriptions, subagent specs), snapshots + rollback, evidence-backed update rules; extends `agent/curator.py` + `learning/`.
- [x] **Phase 57: Agent loop upgrade** - Goals engine, heartbeats/schedules, autonomous mode (turn/token/time budgets + quality gates), agent-to-agent messaging; per-capability enable/disable config (default off); degraded mode with structured warnings; Hermes+Omp regression parity.
- [ ] **Phase 58: Connector layer + parity suite** - Typed Python adapters exposing the ported capabilities through registry/roster; contract tests on both sides; failure-injection tests; behavior-parity fixtures generated from the Rust baseline.
- [ ] **Phase 59: Repository hardening** - AGPL-3.0 LICENSE (Spectrum Web Co 2026) + headers; root file set audit; README rewrite with three-source architecture diagram; docs (ADR-0001, connectors.md, agent-loop.md, migration.md); supply-chain CI (cargo-deny, pip-audit, dependabot); issue/PR templates.
- [ ] **Phase 60: Milestone audit + closeout** - Audit, archive v10 phase dirs to `milestones/v10-phases/`, collapse ROADMAP, cleanup.

## Phase Details

### Phase 53: Prime discovery + parity baseline

**Goal**: Every Prime capability to be ported is mapped to a source
`crate::module` / rlm module with must-preserve behaviors cited, and to an
Omega Prime merge target; the Rust workspace's own test suite passes as
the parity baseline; the upstream pin is recorded.
**Depends on**: v9 complete
**Requirements**: DISC-01, DISC-02, DISC-03
**Success Criteria** (what must be TRUE):

  1. `.planning/research/v10-prime-capability-map.md` covers the required
     capability list with file-cited behaviors.
  2. `.planning/research/v10-omega-overlap-map.md` names the exact
     integration points (registry, roster, prompt assembly, loop phases,
     config) with file citations.
  3. `cargo test --workspace --locked` in `prime-agent/` exits 0 on the
     recorded toolchain; the result is logged as the parity baseline.
  4. `VENDOR.md` records the prime-agent remote, pin, license, and scope.

Plans:

- [x] 53-01: Capability map + overlap map + Rust baseline

### Phase 54: Rust workspace CI integration

**Goal**: CI keeps the parity oracle green on every change: the
prime-agent workspace builds and tests on a pinned toolchain with locked
dependencies, cargo-deny enforces the license allowlist for that
workspace, and builds are cached.
**Depends on**: 53
**Requirements**: BUILD-01, BUILD-02, BUILD-03
**Success Criteria**:

  1. A CI workflow job runs `cargo build --locked` + `cargo test
     --workspace --locked` for `prime-agent/` on the pinned toolchain.
  2. `cargo deny check licenses` runs against the prime-agent workspace
     with an AGPL-compatible allowlist.
  3. The Rust toolchain version is pinned in-repo and matches CI.
  4. Python gates (`pytest`, evals, assemble check) still pass unchanged.

Plans:

- [x] 54-01: Parity-oracle CI job + toolchain pin + deny gate

### Phase 55: RLM recursion port

**Goal**: The agent can spawn child agents programmatically mid-turn with
Prime's RLM semantics — spawn returns a handle, collect settles children,
list/delete inspect and reap, create_session mints durable child sessions,
progress notes flow child→parent — as rostered tools on top of the
existing delegate machinery, with persistent working context across calls.
**Depends on**: 53
**Requirements**: RLM-01, RLM-02, RLM-03, RLM-04
**Success Criteria**:

  1. `rlm_spawn`/`rlm_collect`/`rlm_list_subagents`/`rlm_delete_subagent`/
     `rlm_create_session`/`rlm_progress_note` dispatch through the registry
     and appear on the roster.
  2. Spawn/collect semantics match the Prime behavior spec cited in the
     capability map (handle shape, settled/terminal states, error
     surfaces), proven by scripted-model tests.
  3. Child isolation rules hold: children see their own context; the
     parent sees results through collect, never mid-run state.
  4. Full suite + evals + assemble check pass.

Plans:

- [x] 55-01: RLM recursion tools + semantics port

### Phase 56: Continual harness port

**Goal**: `/refine` reviews the current trajectory and applies small,
evidence-backed updates to supplemental harness state (prompts, memories,
skill descriptions, subagent specs) with recorded snapshots and rollback;
the immutable base system prompt is never rewritten.
**Depends on**: 55
**Requirements**: HARN-01, HARN-02, HARN-03, HARN-04
**Success Criteria**:

  1. Harness state CRUD exists with the four scopes and persists across
     turns.
  2. A refine pass produces a reviewable diff, applies only
     evidence-backed changes, and records a snapshot that rollback
     restores.
  3. The base system prompt bytes are unchanged by any refine pass (test).
  4. Full suite + evals + assemble check pass.

Plans:

- [x] 56-01: Harness state + refine loop + snapshots

### Phase 57: Agent loop upgrade

**Goal**: Goals, heartbeats/schedules, autonomous mode (turn/token/time
budgets with quality gates), and agent-to-agent messaging run inside the
one conversation loop; every Prime capability family is individually
enable/disable-able (default off); a failed or disabled Prime capability
degrades with a loud structured warning; with Prime disabled the
Hermes+Omp loop behaves exactly as before.
**Depends on**: 56
**Requirements**: LOOP-01, LOOP-02, LOOP-03, LOOP-04, LOOP-05, LOOP-06,
LOOP-07
**Success Criteria**:

  1. A goal persists across turns until completed/paused/cleared.
  2. A heartbeat re-enters a session on schedule through the existing cron
      machinery.
  3. Autonomous mode continues within configured budgets and runs a
     configured quality gate; hitting a limit stops cleanly.
  4. Two sessions exchange messages through rostered tools.
  5. Each capability family has a config flag, default off; disabled
     families are absent from roster and prompt.
  6. A Prime capability failure logs a structured degradation event and
     the loop continues.
  7. With all Prime flags off, the existing suite passes unmodified and a
     loop transcript fixture matches pre-v10 behavior.
  8. Full suite + evals + assemble check pass.

Plans:

- [x] 57-01: Goals + heartbeats + autonomous mode
- [x] 57-02: Agent messaging + config flags + degraded mode + regression

### Phase 58: Connector layer + parity suite

**Goal**: The ported Prime capabilities sit behind typed Python adapter
modules with versioned contracts; contract tests cover both sides of each
adapter; failure-injection proves the loop survives capability
panic/error/timeout; behavior-parity fixtures generated from the Rust
baseline pin the port's fidelity.
**Depends on**: 57
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04
**Success Criteria**:

  1. Every Prime capability call goes through a typed adapter with a
     versioned schema — no ad-hoc dicts at the boundary.
  2. Contract tests validate request/response shapes on both sides.
  3. Failure-injection tests: capability raise/timeout/bad payload →
     structured error, loop continues, no hang.
  4. Parity fixtures derived from the Rust baseline pass against the
     ported implementation.
  5. Full suite + evals + assemble check pass.

Plans:

- [ ] 58-01: Typed connectors + contract/failure-injection/parity tests

### Phase 59: Repository hardening

**Goal**: The repo reads as a state-of-the-art, enterprise-grade open-source
project: AGPL-3.0 LICENSE with "Copyright (C) 2026 Spectrum Web Co", the
full root file set, a rewritten README with the three-source architecture,
merge documentation (ADR, connector contracts, loop behavior, migration),
and supply-chain CI on both ecosystems.
**Depends on**: 58
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, REPO-05
**Success Criteria**:

  1. `LICENSE` is the full AGPL-3.0 text with the exact copyright line;
     new source files carry SPDX headers.
  2. Root set present: README, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT,
     SECURITY, CODEOWNERS, editor/git configs, issue/PR templates,
     dependabot.
  3. README documents the Hermes+Omp+Prime architecture with a diagram,
     quickstart, dual-toolchain build, and configuration reference; every
     documented command is executed and passes.
  4. `docs/` gains ADR-0001 (merge architecture), connectors.md,
     agent-loop.md, migration.md; GitBook structure stays valid.
  5. Supply-chain CI: cargo-deny (prime-agent workspace), pip-audit,
     dependabot for cargo/pip/github-actions.
  6. Full suite + evals + assemble check + catalog check pass.

Plans:

- [ ] 59-01: License + root files + community automation
- [ ] 59-02: README + docs + supply-chain CI

### Phase 60: Milestone audit + closeout

**Goal**: The milestone audit verifies every requirement with cited
evidence; v10 phase dirs archive to `milestones/v10-phases/`; ROADMAP
collapses; STATE records completion; cleanup runs per convention.
**Depends on**: 59
**Requirements**: DONE-01, DONE-02
**Success Criteria**:

  1. The audit cites a passing command + exit code for every requirement.
  2. ROADMAP/MILESTONES/STATE reflect v10 complete; phase dirs archived.
  3. Full gate suite green on the final tree.

Plans:

- [ ] 60-01: Audit + archive + cleanup
