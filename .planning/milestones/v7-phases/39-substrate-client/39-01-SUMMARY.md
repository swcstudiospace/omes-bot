# Summary 39-01: Substrate client + memory bridge

## What was built

- `omes/substrate/` package: `SubstrateClient` speaking substrate-mcp
  (`POST /brief`, `POST /events`, `GET /healthz`, `POST /mcp`) on the shared
  stdlib `HttpTransport`, authenticated with a brokered Bearer token
  (`SUBSTRATE_TOKEN`, `SUBSTRATE_TOKEN_GROK_BOT` fallback).
- Fail-open brief/emit (`""` / `stored: False` with redacted reason);
  fail-closed `memory_write` (raises `SubstrateError`); fail-open
  `memory_search` (`[]`). Caller bugs (`ValueError`) stay loud.
- `HttpTransport.post_text` for the markdown brief, via a shared `_request`
  + `_check_status` refactor; JSON path behavior unchanged.
- `omes/tests/test_substrate.py`: 22 tests — fake-transport shapes, status
  passthrough, fail-open/closed matrix, malformed envelopes, token-leak
  guard, and real-bytes `post_text` over socketpair scripted peers.

## Verification

`.venv/bin/python -m pytest omes/tests -q` → exit 0, 257 passed
(235 carried + 22 new). No network in tests. No new dependencies.
