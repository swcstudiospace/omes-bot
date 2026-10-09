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
- ✅ **v10 Prime merge** — Phases 53-61 (shipped 2026-10-09; audit passed)
- 🚧 **v11 Grok Bot native** — Phases 62-63 (in progress)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v10-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v10-phases/`.


## v10 Prime merge — reopened gap closure

The archived v10 implementation baseline is retained below. Production wiring
contradicted LOOP-01/02/03/06 during continuation; plans 61-01/02 repaired those
paths. A 32-requirement integration audit then found durability/privacy, typed
consumer, disabled-prompt, historical-fixture and clean-prerequisite gaps; plans
61-03..06 repaired them and a review-repair wave (2026-10-09) cleared two blockers
and fourteen warnings. The final independent audit accounts for 32/32 satisfied
requirements (30 wired, 2 user-approved exceptions for LOOP-07 and REPO-04).

## Phases

- [x] **Phase 53: Prime discovery + parity baseline** - Capability map and overlap map land under `.planning/research/`; the Rust baseline is logged in `VENDOR.md`.
- [x] **Phase 54: Rust workspace CI integration** - CI builds and tests the prime-agent workspace as the parity oracle (pinned toolchain, `--locked`); cargo-deny license gate.
- [x] **Phase 55: RLM recursion port** - `rlm.spawn`/`collect`/`list_subagents`/`delete_subagent`/`create_session`/`progress_note` and persistent-REPL semantics ported into `omega_prime`.
- [x] **Phase 56: Continual harness + /refine port** - Port `/refine`, rollback, learning, and prompt preservation into the one agent.
- [x] **Phase 57: Agent loop upgrade: goals, heartbeats, autonomous, messaging** - Real goal continuation, APScheduler-bound heartbeats, autonomous turn limits, and agent messaging.
- [x] **Phase 58: Connector layer + parity suite** - Typed, versioned connectors and strict parity fixtures for all 7 Prime capability families.
- [x] **Phase 59: Repository hardening + enterprise open source** - Full AGPL-3.0 licensing, SPDX headers, community files, docs, and supply-chain gates.
- [x] **Phase 60: Milestone audit + closeout** - Initial v10 milestone audit and verification closeout.
- [x] **Phase 61: Prime loop gap closure** - Gap closure across production loop, heartbeat scheduling, typed adapters, RLM durability, and prime-agent submodule integration.

## Phase Details

### Phase 53: Prime discovery + parity baseline

**Goal**: Every Prime capability to be ported is mapped to a source
`crate::module` / rlm module with must-preserve behaviors cited, and to an
Omega Prime merge target; the Rust workspace test baseline is recorded
in `VENDOR.md` (the unskipped run is not exit 0); the upstream pin is
recorded.
**Depends on**: v9 complete
**Requirements**: DISC-01, DISC-02, DISC-03
**Success Criteria** (what must be TRUE):

  1. `.planning/research/v10-prime-capability-map.md` covers the required
     capability list with file-cited behaviors.
  2. `.planning/research/v10-omega-overlap-map.md` names the exact
     integration points (registry, roster, prompt assembly, loop phases,
     config) with file citations.
  3. `cargo test --workspace --locked` on the recorded toolchain is logged
     in `VENDOR.md`. The Phase 53 unskipped fail-fast run exited 101;
     “622 passed” is that run’s partial sum, not a workspace total. The
     accepted gate is the three ACP skips in `prime-agent.pin.json`. A
     later path-clean no-fail-fast accounting of the default targets is
     5089 passed, 2 failed, 19 ignored, 3 filtered. The two failures are
     local ext4 hazards, not pin skips.
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

- [x] 58-01: Typed connectors + contract/failure-injection/parity tests

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

- [x] 59-01: License + root files + community automation
- [x] 59-02: README + docs + supply-chain CI

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

- [x] 60-01: Audit + archive + cleanup


### Phase 61: Prime loop gap closure

**Goal:** The production conversation loop drives the existing Prime goal and
autonomous helpers, and the scheduler re-enters named live sessions for
heartbeats. Capability failures degrade without killing the loop.
**Requirements**: RLM-03, RLM-04, LOOP-01, LOOP-02, LOOP-03, LOOP-04, LOOP-05, LOOP-06, LOOP-07, CONN-01, CONN-03, REPO-04, REPO-05, DONE-01, DONE-02
**Depends on:** Phase 60 archived implementation baseline
**Success Criteria**:

1. A real conversation turn accrues all model-call usage to the persisted
   active goal and delivers continuation prompts; pause, completion, stale
   state, and budgets stop continuation honestly.
2. Production heartbeat scheduling delivers a due persisted job to the
   correct named live session, preserving its transcript and serializing
   with foreground turns. No store lock is held across model calls.
3. Autonomous start/status/stop tools share the driver the loop actually
   consults. Turn/token/time caps and real shell quality gates govern
   continuation without resetting the outer call budget.
4. A failing enabled Prime hook emits a redacted `prime_degraded` event,
   disables continuation from that hook, and leaves the normal response
   available. Provider failures and interrupts are not suppressed.
5. Default-off behavior, approval/roster enforcement, messaging, provider
   metadata, and the existing suite remain intact. Runtime smoke and final
   gates precede updated verification and milestone completion claims.

**Plans:** All six plans are executed with summaries (full suite 983 passed; independent post-repair review clean; final 32-ID audit satisfied: 30 wired + 2 user-approved exceptions for LOOP-07 and REPO-04, 0 open). Milestone closed 2026-10-09: `milestones/v10-MILESTONE-AUDIT.md` status passed; `prime-agent` registered as a git submodule.

Plans:
- [x] 61-01: Goal/autonomous turn boundaries and degradation integration
- [x] 61-02: Named-session heartbeat scheduling and serialization
- [x] 61-03: Connect real registered consumers to typed/versioned adapters and consumer failure recovery
- [x] 61-04: Recoverable RLM child sessions, owned progress and collect-only answers
- [x] 61-05: Config-derived effective prompt/roster and truthful enabled-tool catalog
- [x] 61-06: Authentic pre-v10 transcript comparison, clean Python prerequisite and final parent integration

## v11 Grok Bot native - in progress

Omega Prime becomes a production-grade, enterprise-ready Grok Bot tool host with a
one-command install. Source plan: ultrathink graph `ut-mv0nfl17-58362dc4` (Linear
SPE-8895..SPE-8900), translated from its stack-agnostic wording to this Python MCP host.
User direction (2026-10-09): push to `main` with `prime-agent` as a git submodule.

- [x] **Phase 62: Grok Bot native runtime completion** - Bootstrap/config, health, lifecycle and transport components finished and proven over a real socket.
- [ ] **Phase 63: Seven enterprise improvements** - Streamable HTTP, scoped credentials, approval gateway, traffic protection, observability, live verifier, deployment kit.

### Phase 62: Grok Bot native runtime completion

**Goal**: The shipped `omega_prime/grokbot/` package (commit 5e4775f) is correct,
secure by default and truthful: the remote host fails closed, audits every call,
reports honest health, drains on SIGTERM, and a one-command launcher attaches it.
**Depends on**: Phase 61 (v10 closed)
**Requirements**: GRK-01, GRK-02, GRK-03, GRK-04, GRK-05, GRK-06, GRK-07, GRK-08, GRK-09, GRK-10
**Success Criteria** (what must be TRUE):

  1. Over a real socket, `/sse` without a valid bearer token is 401, a disallowed
     Origin is rejected, and an authenticated MCP client lists exactly the tools
     `/healthz` reports and can call one.
  2. The server refuses to start on a non-loopback bind without a token, and on an
     invalid policy or roster, on both transports, exiting 2 with a reason.
  3. Every remote tool call and auth failure is in a hash-chained audit log that
     `python -m omega_prime.grokbot.audit verify` accepts and rejects after an edit.
  4. The manifest lists the tools actually served, never embeds a token, and
     `sync --check` reports no drift against a fresh export for the same settings.
  5. `oneclick --dry-run` exits 0; a failing preflight exits 3; SIGTERM drains and
     exits 0; `supervisor --stop` stops the supervisor and its child.
  6. Full suite, evals, assemble check, catalog check, `ruff`, `mypy` pass.

Plans:

- [x] 62-01: Bearer security core + tool-call interceptors
- [x] 62-02: Tamper-evident audit log
- [x] 62-03: Truthful manifest, template lint, drift sync
- [x] 62-04: Supervisor and lifecycle fixes
- [x] 62-05: Remote host - fail-closed transport, health/readiness, graceful shutdown, real-transport E2E
- [x] 62-06: 1-click launcher, doctor, emulator

### Phase 63: Seven enterprise improvements

**Goal**: Seven additive capabilities take the host from correct to enterprise-ready:
current-standard transport, credential management, human approval, traffic protection,
observability, a live proof, and a deployment kit.
**Depends on**: Phase 62
**Requirements**: GRI-01, GRI-02, GRI-03, GRI-04, GRI-05, GRI-06, GRI-07
**Success Criteria** (what must be TRUE):

  1. An MCP client connects over Streamable HTTP at `/mcp` and over legacy SSE with the
     same auth, origin and audit behavior.
  2. A revoked or expired token stops working without a restart; a `call` token cannot
     reach `/admin/*`; an admin token can approve a gated tool with a TTL and the call
     then succeeds, with both actions audited.
  3. A burst beyond the limit gets 429 with `Retry-After`; repeated infrastructure
     failures open a per-tool breaker that recovers after the cooldown.
  4. `/metrics` exposes request, tool-call, auth-failure and latency series; responses
     and audit records carry the request id; `--log-format json` emits redacted NDJSON.
  5. `python -m omega_prime.grokbot.verify` passes against a freshly started host over
     both transports and fails against a misconfigured one.
  6. `deploy render` output for all four targets parses and passes the hardening checks;
     `docker build --check` accepts the Dockerfile.
  7. Full suite, evals, assemble check, catalog check, docs tests, `ruff`, `mypy` pass.

Plans:

- [ ] 63-01: Streamable HTTP transport (GRI-01)
- [ ] 63-02: Scoped, rotatable credentials + token CLI (GRI-02)
- [ ] 63-03: Human approval gateway (GRI-03)
- [ ] 63-04: Traffic protection - rate limits + circuit breaker (GRI-04)
- [ ] 63-05: Observability - metrics, trace context, NDJSON logs (GRI-05)
- [ ] 63-06: Live conformance verifier, served manifest + launcher self-test (GRI-06)
- [ ] 63-07: Deployment kit + image CI (GRI-07)
- [ ] 63-08: Integration wiring, docs, milestone audit
