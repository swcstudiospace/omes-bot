# Substrate surface

Omega Prime is a surface on the agent substrate: the shared briefing, event
trail, memory, and docs plane that every agent on the install uses. When
the surface is wired, turns open with a brief of what other agents are
doing, report their own tool trail with graph provenance, share memory
across agents, recall episodes from Hindsight, and answer docs questions
from RAGflow. When it is not wired, Omega Prime runs fully local — the substrate
never blocks a turn.

## What is wired to what

| Omega Prime side | Substrate side | Backed by (Railway) |
| --- | --- | --- |
| Brief on session open | `POST /brief` | TimescaleDB index |
| Turn/tool/file/session events | `POST /events` | GreptimeDB ledger |
| Shared memory write/search | `memory_write` / `memory_search` | TimescaleDB index |
| Docs answers | `docs_search` tool | RAGflow |
| Episodic retain/recall/reflect | Hindsight service, `ultrathink` bank | hindsight-api |
| Task claims + leases | `substrate_graph_*` tools | TimescaleDB index |

Omega Prime never touches GreptimeDB, TimescaleDB, or DragonflyDB directly. Those
are backing stores; only substrate-mcp holds their clients. A store-lock
test (`omega_prime/tests/test_store_lock.py`) fails the build if a direct client
appears under `omega_prime/`.

## Environment

| Variable | Meaning | Default |
| --- | --- | --- |
| `SUBSTRATE_URL` | substrate-mcp base URL | `http://127.0.0.1:7410` |
| `SUBSTRATE_TOKEN` | bearer token (or `SUBSTRATE_TOKEN_GROK_BOT`) | — |
| `HINDSIGHT_URL` | hindsight-api base URL | Railway hindsight-api |
| `HINDSIGHT_API_KEY` | bearer token (or `HINDSIGHT_API_TOKEN`) | — |

Tokens resolve through the credential broker and are redacted from
transcripts, events, and errors. `omega-prime-setup-check` reports which names are
set (never values); unset means the surface stays local.

## Failure behavior

| Call | On outage |
| --- | --- |
| Brief, events, docs/memory search | Fail open: empty brief, `stored: false`, empty results |
| Shared memory writes, graph ops | Fail closed: the caller gets an explicit error |
| Hindsight retain/recall | Falls back to the local bank-tagged store |
| Reflect, page search | Degrade to empty |

Briefs are cached per session and written to `.substrate/BRIEF.md` as the
offline fallback. Tool summaries carry names and file paths only — tool
arguments never leave the process; prompt summaries are truncated and pass
through broker redaction.

## Probes

Four read-only checks, run by hand (never in CI):

```bash
.venv/bin/python -m omega_prime.substrate.probes
```

They hit substrate `/healthz` + `/brief` and hindsight `/health` +
`/version`, print one line each, and exit 0 only when all pass. No probe
emits, retains, writes, or claims anything.

## Add-Bot note

The Grok Bot template runs unwired: xAI's computer cannot reach a
`localhost` substrate-mcp, and templates carry no secrets. Wired mode is
for self-hosted runs — the tool host or any checkout with `SUBSTRATE_URL`
pointing at a reachable substrate-mcp.
