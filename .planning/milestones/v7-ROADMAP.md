# Roadmap: Omes Bot

## Milestones

- ✅ **v1 One Omes agent** — Phases 1-12 (shipped 2026-10-03)
- ✅ **v2 Enterprise hardening** — Phases 13-16 (shipped 2026-10-03)
- ✅ **v3 Grok Bot** — Phases 17-20 (shipped 2026-10-03)
- ✅ **v4 Third-party integrations** — Phases 21-25 (shipped 2026-10-03)
- ✅ **v5 Desk packs** — Phases 26-33 (shipped 2026-10-03)
- ✅ **v6 Grok ship** — Phases 34-38 (shipped 2026-10-03)
- 🚧 **v7 Substrate surface** — Phases 39-43 (in progress)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v6-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v6-phases/`.

## v7 Overview

v6 shipped the Add-Bot product (see `milestones/v6-ROADMAP.md`). v7 plugs
Omes Bot into the Railway substrate plane the way `agent-substrate` defines
it: Omes becomes a substrate surface — brief-on-open, turn/tool event trail
with graph provenance, shared memory through substrate-mcp, episodic memory
through the Hindsight service (shared `ultrathink` bank), docs through
RAGflow-backed `docs_search` — with an explicit, test-enforced ban on direct
GreptimeDB/TimescaleDB/DragonflyDB clients. Numbering continues. A phase is
done when its success criteria pass against fakes/scripted peers; live
Railway probes are opt-in and read-only.

## Phases

- [x] **Phase 39: Substrate client** - brief/emit/memory over substrate-mcp. (completed 2026-10-03)
- [x] **Phase 40: Hindsight episodic** - Retain/recall/reflect on the shared bank. (completed 2026-10-03)
- [x] **Phase 41: Loop wiring + docs** - Brief-on-open, turn events, docs_search. (completed 2026-10-03)
- [x] **Phase 42: Graph + store lock** - Coordination ops, no-direct-clients ban. (completed 2026-10-03)
- [x] **Phase 43: Evals + ship** - Live probes, setup check, template, docs. (completed 2026-10-03)

## Phase Details

### Phase 39: Substrate client

**Goal**: Omes speaks substrate-mcp: brief, events, shared memory.
**Depends on**: v6 complete
**Requirements**: SUB-01, SUB-02
**Success Criteria** (what must be TRUE):

  1. Brief, emit, and health calls run over the stdlib transport with a brokered Bearer token; brief/emit never raise into the turn (fail-open with timeouts), proven by fake-backed tests.
  2. memory_write surfaces accepted/conflict/quarantined/denied and memory_search returns entries; the local store remains the offline fallback.

Plans:

- [x] 39-01: Substrate client + memory bridge

### Phase 40: Hindsight episodic

**Goal**: Episodic retain/recall/reflect against the shared bank.
**Depends on**: Phase 39
**Requirements**: HIN-01, HIN-02
**Success Criteria** (what must be TRUE):

  1. Retain and recall hit the hindsight-api bank routes with the shared `ultrathink` default and the local bank call shape; offline falls back to the local bank, proven by fake-backed tests.
  2. Reflect and knowledge-page search are exposed; the API key is brokered, transcripts redacted, failures fail open.

Plans:

- [x] 40-01: Hindsight service client + fallback

### Phase 41: Loop wiring + docs

**Goal**: The loop lives on the substrate; docs answer from RAGflow.
**Depends on**: Phase 40
**Requirements**: SUB-03, RAG-01
**Success Criteria** (what must be TRUE):

  1. Sessions open with a brief injected (BRIEF.md fallback) and emit session/prompt/tool/file/session-end events with surface + graph_id provenance, proven by fake-backed tests.
  2. A docs_search tool returns RAGflow citations via substrate MCP, or a clear error when the plane is unconfigured.

Plans:

- [x] 41-01: Loop events + docs_search tool

### Phase 42: Graph + store lock

**Goal**: Task coordination through graph ops; backing stores untouched.
**Depends on**: Phase 41
**Requirements**: GRP-01, LOCK-01
**Success Criteria** (what must be TRUE):

  1. claim/release/complete/heartbeat coordinate desk-pack handoffs with lease handling, proven by fake-backed tests.
  2. A store-lock test fails the build if any GreptimeDB/TimescaleDB/DragonflyDB client exists under `omes/`.

Plans:

- [x] 42-01: Graph ops + store-lock guard

### Phase 43: Evals + ship

**Goal**: The surface is proven, documented, and shippable.
**Depends on**: Phase 42
**Requirements**: PRB-01, SHP-01
**Success Criteria** (what must be TRUE):

  1. Opt-in read-only live probes (substrate healthz, hindsight health, brief fetch) run manually against Railway with no secrets printed and no CI dependency.
  2. Substrate eval cases pass, setup_check covers the surface env, the Grok Bot template/routines name the surface, and a GitBook docs page describes it.

Plans:

- [x] 43-01: Probes, evals, template, docs
