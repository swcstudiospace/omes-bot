# Requirements: v7 Substrate surface

Milestone-scoped. v6 requirements are archived in `milestones/v6-REQUIREMENTS.md`.
Ground truth: `~/src/repos/agent-substrate` (`docs/governance.md`,
`docs/grokbot-production-loop.md`, `packages/mcp-server/src/`), the Hindsight
OpenAPI spec (`/openapi.json` on hindsight-api v0.9.1), and the Railway service
inventory (Ultrathink + Agent Substrate projects, production env).
User decisions (2026-10-03): substrate-mediated direction (no direct backing-store
clients), shared `ultrathink` Hindsight bank, fakes + opt-in live probes.

## Substrate client

- [x] **SUB-01**: Omes speaks substrate-mcp over HTTP (`POST /brief`, `POST /events`,
  `GET /healthz`, `POST /mcp`) on the existing stdlib transport with a brokered
  Bearer token; brief and emit are fail-open (timeouts, never raise into the turn).
- [x] **SUB-02**: Shared memory bridge: `memory_write` (accepted/conflict/quarantined/
  denied surfaced to the caller) and `memory_search`; the local file store stays as
  the offline fallback.
- [x] **SUB-03**: Brief injected on session open with `.substrate/BRIEF.md` fallback;
  turn emits `session.start`/`prompt`/`tool.call`/`file.edit`/`session.end` with
  surface + graph_id provenance.

## Hindsight episodic

- [x] **HIN-01**: Retain/recall against the Railway hindsight-api (`POST
  /v1/default/banks/{bank}/memories`, `.../recall`) with the shared `ultrathink`
  bank default; same call shape as the local `Hindsight` bank, which stays as the
  offline fallback.
- [x] **HIN-02**: Reflect + knowledge-page search exposed for deep memory; API key
  brokered, transcripts redacted, failures fail open.

## Docs + graph coordination

- [x] **RAG-01**: `docs_search` tool via substrate MCP (RAGflow-backed retrieval);
  returns citations when a dataset answers, or a clear error when unconfigured.
- [x] **GRP-01**: Graph coordination ops (`graph_claim`/`graph_release`/`graph_complete`,
  heartbeat) for desk-pack task handoff with lease handling.
- [x] **LOCK-01**: No direct GreptimeDB/TimescaleDB/DragonflyDB clients anywhere under
  `omes/`; a store-lock test fails the build on violation (grep + import guard).

## Evals + ship

- [x] **PRB-01**: Opt-in read-only live probes (substrate `healthz`, hindsight `health`,
  brief fetch) runnable manually against Railway; secrets never printed, never in CI.
- [x] **SHP-01**: Substrate eval cases, `setup_check` extension (env presence, no secret
  values), Grok Bot template/routine updates, and a GitBook docs page for the surface.

## Future Requirements (deferred)

- Signed handoff packets (`graph_handoff` is a Phase 2 stub upstream).
- Lease steal handling + drift scan (upstream Phase 2).
- A2A Agent Cards / teachables on Solana (upstream Phase 4/6).
- OTLP tracing from Omes turns (upstream Phase 1 SLO work).

## Out of Scope

- Direct Greptime/Timescale/Dragonfly access from Omes — explicitly forbidden by
  LOCK-01 and the upstream store lock; those stays behind substrate-mcp.
- A second Hindsight bank or bank management UI — one shared `ultrathink` bank.
- Live writes in CI — all committed tests use fakes/scripted peers (PD-1, PD-4).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SUB-01 | Phase 39 | Done |
| SUB-02 | Phase 39 | Done |
| HIN-01 | Phase 40 | Done |
| HIN-02 | Phase 40 | Done |
| SUB-03 | Phase 41 | Done |
| RAG-01 | Phase 41 | Done |
| GRP-01 | Phase 42 | Done |
| LOCK-01 | Phase 42 | Done |
| PRB-01 | Phase 43 | Done |
| SHP-01 | Phase 43 | Done |

**Coverage:** 10/10 Done.
