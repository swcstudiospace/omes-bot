# Requirements: Omega Prime v10 Prime merge

**Defined:** 2026-10-08
**Core Value:** One Omega Prime agent runs three agents' logic — Hermes, Omp,
and Prime — in one Python process, with Prime's differentiating capabilities
ported behavior-faithfully and the repo hardened to enterprise open-source
standards under AGPL-3.0.

## v10 Requirements

### Discovery

- [ ] **DISC-01**: `.planning/research/v10-prime-capability-map.md` covers the
  required capability list (RLM recursion surface, persistent REPL, continual
  harness + /refine, goals, heartbeats/schedules, autonomous mode, agent
  messaging, compaction, executable skills, daemon supervision + session
  persistence, system-prompt layering) with every must-preserve behavior cited
  to a source file
- [ ] **DISC-02**: `.planning/research/v10-omega-overlap-map.md` names the exact
  Omega Prime integration points (registry, roster, prompt assembly, loop
  phases, config, durability) with file citations
- [ ] **DISC-03**: `cargo test --workspace --locked` in `prime-agent/` exits 0
  on the recorded toolchain; the result is logged as the parity baseline and
  `VENDOR.md` records the pin

### Build / CI

- [ ] **BUILD-01**: CI runs `cargo build --locked` and `cargo test
  --workspace --locked` for the prime-agent workspace on the pinned toolchain
- [ ] **BUILD-02**: `cargo deny check licenses` passes against the prime-agent
  workspace with an AGPL-compatible allowlist
- [ ] **BUILD-03**: The Rust toolchain version is pinned in-repo and matches CI

### RLM recursion

- [ ] **RLM-01**: `rlm_spawn` + `rlm_collect` match Prime's handle shape,
  settled/terminal states, and error surfaces, proven by scripted-model tests
- [ ] **RLM-02**: `rlm_list_subagents` + `rlm_delete_subagent` inspect and reap
  children with Prime's status vocabulary
- [ ] **RLM-03**: `rlm_create_session` mints durable child sessions and
  `rlm_progress_note` flows child→parent with Prime's acceptance semantics
- [ ] **RLM-04**: Children are isolated: a child never sees parent context; the
  parent sees results only through collect

### Continual harness

- [ ] **HARN-01**: Harness state CRUD covers supplemental prompts, memories,
  skill descriptions, and subagent specs, persisted across turns
- [ ] **HARN-02**: A refine pass produces a reviewable diff and applies only
  evidence-backed updates
- [ ] **HARN-03**: Every applied refinement records a snapshot; rollback
  restores the prior state exactly
- [ ] **HARN-04**: The base system prompt bytes are never changed by a refine
  pass (test-enforced)

### Agent loop

- [ ] **LOOP-01**: A goal persists across turns until completed, paused, or
  cleared
- [ ] **LOOP-02**: A heartbeat re-enters a session on schedule through the
  existing cron machinery
- [ ] **LOOP-03**: Autonomous mode continues within configured turn/token/time
  budgets, runs a configured quality gate, and stops cleanly at a limit
- [ ] **LOOP-04**: Two sessions exchange messages through rostered tools
- [ ] **LOOP-05**: Each Prime capability family has a config flag, default off;
  a disabled family is absent from roster and prompt
- [ ] **LOOP-06**: A Prime capability failure logs a structured degradation
  event and the loop continues
- [ ] **LOOP-07**: With all Prime flags off, the pre-v10 suite passes
  unmodified and a loop transcript fixture matches pre-v10 behavior

### Connectors

- [ ] **CONN-01**: Every Prime capability call goes through a typed adapter
  with a versioned schema; no ad-hoc dicts at the boundary
- [ ] **CONN-02**: Contract tests validate request/response shapes on both
  sides of each adapter
- [ ] **CONN-03**: Failure-injection tests prove the loop survives capability
  raise/timeout/bad-payload with a structured error and no hang
- [ ] **CONN-04**: Behavior-parity fixtures derived from the Rust baseline pass
  against the ported implementation

### Repository

- [ ] **REPO-01**: `LICENSE` carries the full AGPL-3.0 text with "Copyright (C)
  2026 Spectrum Web Co"; new source files carry SPDX-License-Identifier:
  AGPL-3.0-only headers; ported Prime code retains MIT attribution
- [ ] **REPO-02**: Root file set present and current: README, CHANGELOG,
  CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CODEOWNERS, .gitignore,
  .gitattributes, .editorconfig, issue/PR templates, dependabot
- [ ] **REPO-03**: `docs/` gains adr/0001-prime-merge-architecture.md,
  connectors.md, agent-loop.md, and migration.md; GitBook structure stays
  valid
- [ ] **REPO-04**: Supply-chain CI runs cargo-deny (prime-agent workspace),
  pip-audit, and dependabot for cargo/pip/github-actions
- [ ] **REPO-05**: README documents the Hermes+Omp+Prime architecture with a
  diagram, quickstart, dual-toolchain build, and configuration reference;
  every documented command is executed and passes

### Closeout

- [ ] **DONE-01**: The milestone audit cites a passing command + exit code for
  every v10 requirement
- [ ] **DONE-02**: ROADMAP/MILESTONES/STATE record v10 complete; phase dirs
  archive to `milestones/v10-phases/`; cleanup runs per convention
