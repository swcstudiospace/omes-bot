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
- ✅ **v11 Grok Bot native** — Phases 62-63 (shipped 2026-10-09; audit passed)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v11-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v11-phases/`.

## v12 Programming Desk merge - scoped 2026-10-09

The dormant seeds activate: SEED-005 (Programming Desk runtime as the native 1-Bot programmer)
and SEED-014 (real end-to-end verification evidence). Source: `/root/src/repos/programming-desk`
pinned at `9de3aa3` — the seven-seat desk OS (LEAD + build seats + QUALITY, verification
receipts, path ownership, executable gates, contract-first cross-bot protocol). Merge direction
(user, 2026-10-09): behavior-port the pattern **under Omega Prime — one bot controlling
subbots**, Grok Bot native; not a second gateway deployment. Every SEED-005 gap re-verified
8/8 CONFIRMED-GAP on this tree (see `milestones/v12-phases/64-*` CONTEXT once archived).

- [x] **Phase 64: Desk runtime activation** - Desk contexts configured (memory/intake/roster/events/substrate/registry), install-vs-work root split, `delegate_task` served, lead pass wired to a production entry point, desk env surface. (DESK-01..04, DESK-08)
- [x] **Phase 65: Receipts, gates and service clients** - Command-capture receipt verification with a real approver, target-aware gates, Railway/Greptile/Vercel/Playwright/Play/ASC clients behind credentials. (DESK-05..07)
- [ ] **Phase 66: Grok Bot clone-and-run proof** - Truthful host/manifest/roster for the desk-activated tool set; fresh-clone → attach → desk tool call over a real transport; three-source port evidence; docs. (DESK-09..11)
- [ ] **Phase 67: Milestone audit + closeout** - Per-requirement audit, archive to `milestones/v12-phases/`, roadmap collapse, full gates on the final tree. (DONE-01, DONE-02)

### Phase 64: Desk runtime activation

**Goal**: The desk runtime is real: lead tools return live results, the agent can program a
target repo, subagents are reachable via `delegate_task`, and the lead pass claims intake and
dispatches tickets in production.
**Depends on**: v11 closed
**Requirements**: DESK-01, DESK-02, DESK-03, DESK-04, DESK-08
**Success Criteria** (what must be TRUE):

  1. `lead_doctor` green on memory, tools, substrate over a real host process; intake/roster/
     event stores persist under `OMEGA_PRIME_STATE_DIR`.
  2. Coding/file/terminal/LSP tools operate on a foreign repo via work root; escapes refused;
     install-root lookups unaffected.
  3. `delegate_task` in the served list on both transports; a delegated child turn returns.
  4. `run_lead_pass` reachable from cron/heartbeat with the production dispatch closure;
     intake→receipt→ack E2E on real stores.
  5. Desk env surface documented and wired; unconfigured optionals degrade loudly.
  6. Full gate suite green.

### Phase 65: Receipts, gates and service clients

**Goal**: The desk's verification spine works: receipts machine-checked against captured
command executions with a real approver, gates targeting the work repo, and the five service
clients real behind credentials.
**Depends on**: 64
**Requirements**: DESK-05, DESK-06, DESK-07
**Success Criteria** (what must be TRUE):

  1. `qua_gates_run` runs a target repo's suites and reports real exit codes.
  2. A receipt citing a captured command verifies; a forged exit code fails; the approver
     identity is not the author.
  3. Each service client exercises its API against a live endpoint when credentials exist
     (recorded honestly when they do not), following the env-token + broker pattern.
  4. Full gate suite green.

### Phase 66: Grok Bot clone-and-run proof

**Goal**: A fresh clone attaches to Grok Bot and uses the desk for real; the host tells the
truth about what it serves.
**Depends on**: 65
**Requirements**: DESK-09, DESK-10, DESK-11
**Success Criteria** (what must be TRUE):

  1. Manifest/health/verify/roster agree on the desk-activated tool set; template gate passes.
  2. The documented clone-and-run checklist executed for real in verification, including a
     desk tool call over a real transport.
  3. Hermes/Omp/Prime port evidence re-verified on the final tree with citations.
  4. Full gate suite green.

### Phase 67: Milestone audit + closeout

**Goal**: Independent audit with cited evidence for every requirement; archive and collapse
per convention.
**Depends on**: 66
**Requirements**: DONE-01, DONE-02
**Success Criteria** (what must be TRUE):

  1. Every requirement cites a passing command + exit code.
  2. Phase dirs archived to `milestones/v12-phases/`; ROADMAP collapsed; STATE/state.json
     record completion.
  3. Full gate suite green on the final tree.
