# Requirements: Omega Prime v10 Prime merge

**Defined:** 2026-10-08
**Core Value:** One Omega Prime agent runs three agents' logic — Hermes, Omp,
and Prime — in one Python process, with Prime's differentiating capabilities
ported behavior-faithfully and the repo hardened to enterprise open-source
standards under AGPL-3.0.

## v10 Requirements

### Discovery

- [x] **DISC-01**: `.planning/research/v10-prime-capability-map.md` covers the
  required capability list (RLM recursion surface, persistent REPL, continual
  harness + /refine, goals, heartbeats/schedules, autonomous mode, agent
  messaging, compaction, executable skills, daemon supervision + session
  persistence, system-prompt layering) with every must-preserve behavior cited
  to a source file
- [x] **DISC-02**: `.planning/research/v10-omega-overlap-map.md` names the exact
  Omega Prime integration points (registry, roster, prompt assembly, loop
  phases, config, durability) with file citations
- [x] **DISC-03**: the parity baseline is `cargo test --workspace --locked` on the pinned
  toolchain, with the pin recorded in `VENDOR.md`. Unskipped, that command
  exits 101: three `pa-cli` `acp_mode_e2e` settle tests fail and are the
  skip set in `omega_prime/contracts/prime-agent.pin.json`. CI runs the
  skip set. The Phase 53 “622 passed” figure is the fail-fast sum of
  `test result: ok` lines before `acp_mode_e2e`, not a full-workspace exit 0.
  A later path-clean no-fail-fast accounting of the default targets, with
  those three skips filtered, is 5089 passed, 2 failed, 19 ignored, 3
  filtered (`VENDOR.md`). The two failures are local ext4 hazards
  (`futimens` ctime, import sidecar `readdir` order), not pin exclusions

### Build / CI

- [x] **BUILD-01**: CI runs `cargo build --locked` and `cargo test
  --workspace --locked` for the prime-agent workspace on the pinned toolchain
- [x] **BUILD-02**: `cargo deny check licenses` passes against the prime-agent
  workspace with an AGPL-compatible allowlist
- [x] **BUILD-03**: The Rust toolchain version is pinned in-repo and matches CI

### RLM recursion

- [x] **RLM-01**: `rlm_spawn` + `rlm_collect` match Prime's handle shape,
  settled/terminal states, and error surfaces, proven by scripted-model tests
- [x] **RLM-02**: `rlm_list_subagents` + `rlm_delete_subagent` inspect and reap
  children with Prime's status vocabulary
- [x] **RLM-03**: `rlm_create_session` mints durable child sessions and
  `rlm_progress_note` flows child→parent with Prime's acceptance semantics
- [x] **RLM-04**: Children are isolated: a child never sees parent context; the
  parent sees results only through collect

### Continual harness

- [x] **HARN-01**: Harness state CRUD covers supplemental prompts, memories,
  skill descriptions, and subagent specs, persisted across turns
- [x] **HARN-02**: A refine pass produces a reviewable diff and applies only
  evidence-backed updates
- [x] **HARN-03**: Every applied refinement records a snapshot; rollback
  restores the prior state exactly
- [x] **HARN-04**: The base system prompt bytes are never changed by a refine
  pass (test-enforced)

### Agent loop

- [x] **LOOP-01**: A goal persists across turns until completed, paused, or
  cleared
- [x] **LOOP-02**: A heartbeat re-enters a session on schedule through the
  existing cron machinery
- [x] **LOOP-03**: Autonomous mode continues within configured turn/token/time
  budgets, runs a configured quality gate, and stops cleanly at a limit
- [x] **LOOP-04**: Two sessions exchange messages through rostered tools
- [x] **LOOP-05**: Each Prime capability family has a config flag, default off;
  a disabled family is absent from roster and prompt
- [x] **LOOP-06**: A Prime capability failure logs a structured degradation
  event and the loop continues
- [x] **LOOP-07**: With all Prime flags off, the pre-v10 suite passes
  unmodified and a loop transcript fixture matches pre-v10 behavior
  *(user-approved exception, 2026-10-09: the transcript fixture half passes 6/6
  against a pristine pre-v10 checkout; the unmodified historical suite replays as
  376 passed / 2 failed, identical before and after the review-repair wave, and the
  two failures are catalog/roster inventory pins that cannot hold once Prime tools
  exist. No test was edited, deleted or shimmed.)*

### Connectors

- [x] **CONN-01**: Every Prime capability call goes through a typed adapter
  with a versioned schema; no ad-hoc dicts at the boundary
  *(documented scope accepted by the user, 2026-10-09: all 37 registered Prime tools
  of seven families and the kernel bridge's declared keys decode through versioned
  typed requests, mechanically proven; loop-internal goal accrual and driver consult
  use the live store/driver with typed response views, and the kernel wire ignores
  undeclared SDK kwargs. See docs/connectors.md.)*
- [x] **CONN-02**: Contract tests validate request/response shapes on both
  sides of each adapter
- [x] **CONN-03**: Failure-injection tests prove the loop survives capability
  raise/timeout/bad-payload with a structured error and no hang
- [x] **CONN-04**: Behavior-parity fixtures derived from the Rust baseline pass
  against the ported implementation

### Repository

- [x] **REPO-01**: `LICENSE` carries the full AGPL-3.0 text with "Copyright (C)
  2026 Spectrum Web Co"; new source files carry SPDX-License-Identifier:
  AGPL-3.0-only headers; ported Prime code retains MIT attribution
- [x] **REPO-02**: Root file set present and current: README, CHANGELOG,
  CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CODEOWNERS, .gitignore,
  .gitattributes, .editorconfig, issue/PR templates, dependabot
- [x] **REPO-03**: `docs/` gains adr/0001-prime-merge-architecture.md,
  connectors.md, agent-loop.md, and migration.md; GitBook structure stays
  valid
- [x] **REPO-04**: Supply-chain CI runs cargo-deny (prime-agent workspace),
  pip-audit, and dependabot for cargo/pip/github-actions
  *(user-approved exception, 2026-10-09: no Cargo Dependabot. The Cargo path
  dependencies live in the ignored read-only prime-agent checkout, so a source-only
  `cargo metadata --locked` exits 101 and Dependabot cannot resolve them; cargo-deny
  and pip-audit run, pip and github-actions Dependabot are configured.)*
- [ ] **REPO-05**: README documents the Hermes+Omp+Prime architecture with a
  diagram, quickstart, dual-toolchain build, and configuration reference;
  every documented command is executed and passes
  *(open, human needed: the documented commands pass on an isolated snapshot of the
  working tree (fresh venv, pinned public checkout: 949 passed / 13 skipped, setup 0)
  and over a real stdio MCP server, but all v10 work is uncommitted so the published
  repository cannot reproduce it; needs a published revision or the user's acceptance
  of the snapshot evidence, plus a current receipt or acceptance for the optional
  upstream cargo build.)*

### Closeout

- [ ] **DONE-01**: The milestone audit cites a passing command + exit code for
  every v10 requirement
  *(open: `.planning/v10-MILESTONE-AUDIT.md` is written with commands and exit codes
  for all 32 IDs and records the two user-approved exceptions; it stays gaps_found
  while REPO-05 is open.)*
- [ ] **DONE-02**: ROADMAP/MILESTONES/STATE record v10 complete; phase dirs
  archive to `milestones/v10-phases/`; cleanup runs per convention
  *(not started by user decision, 2026-10-09: stop before the irreversible lifecycle;
  no completion, archive, cleanup, commit or PR.)*


## Reopened v10 gap-closure traceability

The archive remains historical. Checked requirements below retain their
archived evidence and are covered by current regression gates; they are not
claims of a new native engine/daemon integration. The four loop wiring gaps
and final audit/completion records are reopened for Phase 61.

The current audit repairs the inherited refine/rollback defect (HARN-03),
exercises fixed-prompt bytes (HARN-04), adds native bridge license/CI coverage,
and corrects the broken clone URL. REPO-04 is reopened: Cargo Dependabot cannot
fetch the required path manifests from the ignored Prime checkout. Making that
checkout repository-fetchable or accepting an explicit scope exception requires
a user decision; no Cargo automation success is claimed.

DONE-01 and DONE-02 stay blocked until the complete requirement audit and actual
archive/cleanup succeed. Their blocked rows prevent phase completion from
prematurely checking milestone lifecycle requirements.

The final independent integration checker (`FinalV10Integration`, read-only,
unsigned; `phases/61-prime-loop-gap-closure/61-INTEGRATION.md`) accounts for all 32 IDs
after the review-repair wave: 27 WIRED, 3 BROKEN (LOOP-07, REPO-04, DONE-01) and
2 HUMAN_NEEDED (REPO-05, DONE-02). On 2026-10-09 the user approved two criterion
exceptions (LOOP-07 literal unmodified historical suite; REPO-04 Cargo Dependabot),
accepted the documented CONN-01 scope, and chose to stop before the irreversible
milestone lifecycle. Those decisions are recorded in the rows below; they are not
passes of the literal commands, and exit codes 1 (historical replay) and 101 (cargo
metadata) remain the observed facts. Checked requirements marked inherited retain
their archived evidence; this is not a new native engine/daemon milestone.

| Requirement | Phase | Status |
|---|---|---|
| DISC-01 | 53 | Inherited archival evidence; preserve by regression |
| DISC-02 | 53 | Inherited archival evidence; preserve by regression |
| DISC-03 | 53 | Inherited archival evidence; preserve by regression |
| BUILD-01 | 54 | Inherited archival evidence; preserve by regression |
| BUILD-02 | 54 | Inherited archival evidence; preserve by regression |
| BUILD-03 | 54 | Inherited archival evidence; preserve by regression |
| RLM-01 | 55 | Inherited archival evidence; preserve by regression |
| RLM-02 | 55 | Inherited archival evidence; preserve by regression |
| RLM-03 | 61 | Complete |
| RLM-04 | 61 | Complete |
| HARN-01 | 56 | Inherited archival evidence; preserve by regression |
| HARN-02 | 56 | Inherited archival evidence; preserve by regression |
| HARN-03 | 56 | Inherited archival evidence; preserve by regression |
| HARN-04 | 56 | Inherited archival evidence; preserve by regression |
| LOOP-01 | 61 | Complete |
| LOOP-02 | 61 | Complete |
| LOOP-03 | 61 | Complete |
| LOOP-04 | 57 | Inherited archival evidence; preserve by regression |
| LOOP-05 | 61 | Complete |
| LOOP-06 | 61 | Complete |
| LOOP-07 | 61 | Complete (user-approved exception) |
| CONN-01 | 61 | Complete (documented scope accepted) |
| CONN-02 | 58 | Inherited archival evidence; preserve by regression |
| CONN-03 | 61 | Complete |
| CONN-04 | 58 | Inherited archival evidence; preserve by regression |
| REPO-01 | 59 | Inherited archival evidence; preserve by regression |
| REPO-02 | 59 | Inherited archival evidence; preserve by regression |
| REPO-03 | 59 | Inherited archival evidence; preserve by regression |
| REPO-04 | 59 | Complete (user-approved exception) |
| REPO-05 | 61 | Human needed (published revision or acceptance) |
| DONE-01 | 61 | Open (audit gaps_found: REPO-05) |
| DONE-02 | 61 | Not started (user decision: stop before lifecycle) |
