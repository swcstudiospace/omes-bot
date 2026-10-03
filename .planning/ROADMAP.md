# Roadmap: Omes Bot v2

## Overview

v1 built one agent that runs both Hermes and Omp logic (see `milestones/v1-ROADMAP.md`). v2 hardens that agent the way OpenShell and AgentOS harden theirs — declarative policy, a credential broker, durable runs, and real transports — while staying one in-process Python agent with one seat. Numbering continues from v1. A phase is done when its parity checks pass.

## Phases

**Phase Numbering:**

- Integer phases (13, 14, 15, 16): Planned v2 milestone work
- Decimal phases (13.1, 13.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 13: Policy engine** - Seat policy, dispatch enforcement, advisor diffs, and a persisted audit log.
- [ ] **Phase 14: Credential broker** - Env-backed keys injected per approved endpoint, with secret redaction.
- [ ] **Phase 15: Durable runs** - Turn journal with resume, cron execution history, checkpointed workflows.
- [ ] **Phase 16: Transports and traces** - Stdlib HTTP with retries, and structured trace export.

## Phase Details

### Phase 13: Policy engine
**Goal**: A seat policy file governs what the agent may call, write, and reach, and every verdict is auditable.
**Depends on**: v1 complete
**Requirements**: POL-01, POL-02, POL-03, POL-04
**Success Criteria** (what must be TRUE):
  1. A policy file declares allowed tools, path roots with read-only paths, and network hosts.
  2. Dispatch refuses a disallowed tool before execution, and a write to a read-only path is refused with the file unchanged.
  3. The advisor flags added tools, widened paths, and added hosts in a proposed policy change.
  4. Every dispatch appends one record to the persisted audit log.
**Plans**: 1 plan

Plans:
- [x] 13-01: Seat policy, enforcement, advisor, and audit log

### Phase 14: Credential broker
**Goal**: Secrets live in the broker and reach only approved endpoints; transcripts and logs never carry them.
**Depends on**: Phase 13
**Requirements**: CRED-01, CRED-02, CRED-03
**Success Criteria** (what must be TRUE):
  1. Provider keys resolve from the environment through the broker; the agent never handles a key string.
  2. A request to a host outside the policy allowlist gets no credential.
  3. Keys and tokens are redacted in events, audit records, and rendered output.
**Plans**: 1 plan

Plans:
- [ ] 14-01: Broker, per-endpoint injection, and redaction

### Phase 15: Durable runs
**Goal**: Turns, jobs, and workflows survive a crash by resuming from persisted state.
**Depends on**: Phase 14
**Requirements**: DUR-01, DUR-02, DUR-03
**Success Criteria** (what must be TRUE):
  1. A journaled turn resumes after a simulated crash with the transcript intact.
  2. Cron executions are recorded with bounded history, and a completed tick is not re-run.
  3. A three-step workflow interrupted mid-run resumes from its last checkpoint.
**Plans**: 1 plan

Plans:
- [ ] 15-01: Turn journal, cron history, and checkpointed workflows

### Phase 16: Transports and traces
**Goal**: Provider calls run over a real HTTP transport, and turns export structured traces.
**Depends on**: Phase 15
**Requirements**: NET-01, OBS-01
**Success Criteria** (what must be TRUE):
  1. A provider completes a call through the stdlib HTTP transport against a local fixture server, with a retry on a dropped first attempt.
  2. A turn exports a trace with spans for the model call, tool calls, and policy verdicts.
**Plans**: 1 plan

Plans:
- [ ] 16-01: HTTP transport and trace export

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 13. Policy engine | 1/1 | Complete | 2026-10-03 |
| 14. Credential broker | 0/1 | Not started | - |
| 15. Durable runs | 0/1 | Not started | - |
| 16. Transports and traces | 0/1 | Not started | - |
