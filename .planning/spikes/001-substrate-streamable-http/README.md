---
spike: 001
idea: omega-native-integrations
name: substrate-streamable-http
type: standard
validates: "Given the running local substrate-mcp on 127.0.0.1:7410, when Omes's current SubstrateClient MCP shape and the official MCP Python SDK Streamable HTTP client each initialize, list tools and call one tool, then the current shape fails as research predicts while the SDK client negotiates, lists tools and surfaces isError correctly"
verdict: VALIDATED
related: []
tags: [substrate, mcp, streamable-http]
---

# Spike 001: substrate-streamable-http

## What This Validates

Given the running local substrate-mcp (bun, `127.0.0.1:7410`, `GET /healthz` currently
HTTP 503 because its stores are not connected),
when (a) Omes's current `SubstrateClient` request shape for `POST /mcp` and (b) the
official MCP Python SDK (`mcp` 2.3.0 in the repo `.venv`) Streamable HTTP client each
try to initialize, list tools and call a harmless tool,
then (a) fails in the ways the source predicts, and (b) negotiates a protocol version,
lists the tools and returns `CallToolResult.is_error == True` for tool-level errors.

Omega needs to know which client to build on, and what each failure looks like.

## Research

### Sources read

| Source | What it settles |
|---|---|
| `omes/substrate/client.py` | `_mcp_post` sends one bare `tools/call` envelope (no `initialize`, no `MCP-Protocol-Version`, no session handling) through `HttpTransport.post`. `_tool_text` reads `result.content[0].text` and **never looks at `result.isError`**. |
| `omes/providers/http.py` | `HttpTransport.post` sets only `Content-Type: application/json` and `Content-Length` (no `Accept`). 4xx is final (`ProviderError("HTTP 4xx from <url>")`); 408/429/5xx retry twice; the body must be a JSON object (`json.loads`), so an SSE body raises `response is not JSON`. |
| `agent-substrate/packages/mcp-server/src/server.ts` | Auth runs before routing, on **every** path including `/healthz`: no token match and `allowAnonymous == false` → `401 {"error":"unknown or missing bearer token"}`. `/mcp` is **stateless**: a fresh `McpServer` + `StreamableHTTPServerTransport({sessionIdGenerator: undefined})` per POST; non-POST → `405` with `Allow: POST`. `enableJsonResponse` is not set, so replies are `text/event-stream`. Unknown paths → `404` JSON `{"error":"no route for …"}`. |
| `agent-substrate/packages/mcp-server/src/config.ts` | Tokens come only from `SUBSTRATE_TOKEN_<SURFACE>` env vars (`SUBSTRATE_TOKEN_GROK_BOT` → surface `grok-bot`); a bare `SUBSTRATE_TOKEN` is ignored server-side. `allowAnonymous = (no SUBSTRATE_TOKEN_* set)`. A bogus bearer on an anonymous server is accepted (surface falls back to null). |
| `agent-substrate/packages/mcp-server/src/mcp.ts` | 12 tools: `memory_brief`, `memory_write`, `memory_search`, `events_emit`, `graph_get`, `graph_register`, `graph_claim`, `graph_release`, `graph_complete`, `graph_heartbeat`, `graph_handoff`, `docs_search`. Read-only ones used here: `memory_brief`, `graph_get`. |
| TS SDK `@modelcontextprotocol/sdk` 1.30.1 (`packages/mcp-server/node_modules`), `dist/esm/server/webStandardStreamableHttp.js` | POST requires `Accept` containing **both** `application/json` and `text/event-stream`, else `406` JSON-RPC error `-32000 "Not Acceptable: Client must accept both application/json and text/event-stream"`. `Content-Type` must be JSON (`415`). Stateless mode skips session validation, so a bare `tools/call` without `initialize` is allowed. A non-initialize request with `MCP-Protocol-Version` outside `2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05, 2024-10-07` → `400 -32000 "Bad Request: Unsupported protocol version: …"`. Error responses use `id: null`. |
| TS SDK `dist/esm/server/mcp.js` (`McpServer` tools/call handler) | Every tool failure — handler throw, zod input validation, **unknown tool name** — is converted to a `CallToolResult` with `isError: true` and text `"MCP error -32602: …"`, not a JSON-RPC error. So `graph_get {}` and `no_such_tool` deterministically produce `isError` regardless of store state. |
| Python SDK `mcp` 2.3.0 (`.venv`): `client/client.py`, `client/_probe.py`, `client/streamable_http.py` | `Client(url_or_transport, mode="auto"|"legacy"|"2026-07-28")`. `auto` (default) first POSTs `server/discover` at `2026-07-28`; any JSON-RPC error other than `-32022` falls back to `initialize`. Headers/auth go on an `httpx2.AsyncClient` passed as `http_client=`. On a 4xx with a JSON-RPC body the error is surfaced with the request's id; a 4xx with a non-JSON-RPC body becomes `-32603 "Server returned an error response"` (404 before a session → `-32601 "Not Found"`). The GET listen stream is only opened when the server issued a session id (stateless substrate never does). `CallToolResult.is_error` is a first-class field. |
| [MCP Python SDK migration guide v1→v2](https://py.sdk.modelcontextprotocol.io/migration/), [Protocol versions](https://py.sdk.modelcontextprotocol.io/protocol-versions/) | Confirms `mode="auto"` probes `server/discover` then falls back; `mode="legacy"` reproduces the pre-2026 handshake; v1 `streamablehttp_client(headers=…, auth=…)` became `streamable_http_client(url, http_client=httpx2.AsyncClient(...))`. |
| [MisakaNet issue #2871](https://github.com/Ikalus1988/MisakaNet/issues/2871) (third-party, TS client) | Reports that a 2025-era server that 401s the discover probe leaves a v2 client "disconnected". Probe case S04/S05 checks the Python equivalent against a token-mode substrate. |
| `omes/greptile/kb_sync.py` (prior art in this repo) | A hand-rolled streamable-HTTP client that already sends `Accept: application/json, text/event-stream`, runs `initialize` + `notifications/initialized`, echoes `Mcp-Session-Id`, decodes SSE and checks `isError`. Shows Omes already had to re-implement the transport once. |

### Approaches

| Approach | Tool/Library | Pros | Cons | Status |
|---|---|---|---|---|
| Keep current `SubstrateClient._mcp_post` | stdlib `HttpTransport` | sync, zero deps | Missing `Accept` → 406 on every MCP call (source-predicted); no SSE decoding; no handshake; `isError` ignored | Probed (a) |
| Patch `SubstrateClient`: `Accept` both + SSE decode (+ isError check) | stdlib | small diff, stays sync | Re-implements transport/version negotiation by hand; second copy beside `kb_sync.py`; will drift with spec (2026-07-28 discover era) | Probed (a) part 3 (shim, shows isError still swallowed) |
| Official SDK `mcp.Client` + `streamable_http_client` | `mcp` 2.3.0 (already a dependency: `mcp>=2.3,<3`) | spec-tracking, handshake/version fallback, SSE, `is_error` typed, auth via `httpx2` | async (Omes client is sync → needs a sync bridge); `auto` mode costs one failing discover round trip per connection against this TS 1.x server | Probed (b) |

**Chosen approach (to be confirmed by results):** the official SDK client for `/mcp`, keeping the
plain-REST `HttpTransport` for `/healthz`, `/brief`, `/events` (those routes are not MCP).

## How to Run

All commands are read-only against the substrate. Run from the repo root
`/root/src/repos/Omes-Bot`. `-B` keeps Python from writing `__pycache__`.

```bash
# (a) current Omes request shape: raw replay + real SubstrateClient (read-only methods) + SSE shim
.venv/bin/python -B .planning/spikes/001-substrate-streamable-http/probe_omes_shape.py
#   -> .planning/spikes/001-substrate-streamable-http/results-omes-shape.json

# (b) official MCP Python SDK Streamable HTTP client
.venv/bin/python -B .planning/spikes/001-substrate-streamable-http/probe_sdk.py
#   -> .planning/spikes/001-substrate-streamable-http/results-sdk.json
```

Optional auth leg (the 7410 server is anonymous, so it cannot show 401). Starts a
throwaway, store-less, token-mode substrate on `127.0.0.1:17411` with a scrubbed env and
one dummy non-secret token, runs both probes against it, then stops it:

```bash
.planning/spikes/001-substrate-streamable-http/run_token_server.sh   # foreground; run as a background job
# wait for: "[substrate] listening on http://127.0.0.1:17411 (no stores, 1 tokens)"
export SPIKE001_TOKEN=spike001-dummy-token-not-a-secret
.venv/bin/python -B .planning/spikes/001-substrate-streamable-http/probe_omes_shape.py \
  --base-url http://127.0.0.1:17411 --token-env SPIKE001_TOKEN \
  --out .planning/spikes/001-substrate-streamable-http/results-omes-shape-token.json
.venv/bin/python -B .planning/spikes/001-substrate-streamable-http/probe_sdk.py \
  --base-url http://127.0.0.1:17411 --token-env SPIKE001_TOKEN \
  --out .planning/spikes/001-substrate-streamable-http/results-sdk-token.json
# stop the server (SIGTERM/Ctrl-C), then prove it is gone:
ss -ltnp | grep 17411 || echo "17411 closed"
```

## What to Expect

Predictions derived from the source above; **not yet observed** (Results is PENDING).

**(a) `probe_omes_shape.py`, part 1 (raw):**

| Case | Predicted status / content-type | Predicted Omes outcome |
|---|---|---|
| A01 `GET /healthz` | 503 `application/json` `{"index":false,"greptime":false,…}` | retried twice, then `SubstrateError("substrate health failed: request to 127.0.0.1 failed after retries: HTTP 503")` |
| A02 exact Omes shape (no `Accept`) | **406** `application/json` `{"jsonrpc":"2.0","error":{"code":-32000,"message":"Not Acceptable: Client must accept both application/json and text/event-stream"},"id":null}` | `ProviderError("HTTP 406 from http://127.0.0.1:7410/mcp")`, no retry |
| A03 / A04 one media type only | 406, same body | same |
| A05–A08 `Accept` both, no initialize | 200 `text/event-stream`, `event: message` / `data: {…}` | `ProviderError("response is not JSON: …")` (SSE framing) |
| A07 `graph_get {}` / A08 unknown tool | 200 SSE with `result.isError: true` | — |
| A09 initialize | 200 SSE, `protocolVersion: "2025-11-25"`, **no** `mcp-session-id` header | — |
| A11 / A12 `MCP-Protocol-Version: 2026-07-28` | 400 `-32000 "Bad Request: Unsupported protocol version: 2026-07-28 (supported versions: …)"` | — |
| A13 `Content-Type: text/plain` | 415 | — |
| A14 GET / A15 DELETE `/mcp` | 405, `Allow: POST`, empty body | — |
| A16 bogus bearer / A17–A18 no auth (7410, anonymous) | same as authorised | — |
| A16–A18 on the token server | 401 `{"error":"unknown or missing bearer token"}` (also on `/healthz`) | `ProviderError("HTTP 401 …")` |

**Part 2 (real `SubstrateClient`, read-only methods):** `health()` raises after ~0.3 s of
retries; `brief()` returns the brief text (REST, unaffected); `_call_tool` / `_call_tool_text`
raise `SubstrateError("substrate graph_get failed: HTTP 406 from …/mcp")`; `memory_search`
returns `[]` **silently** (fail-open hides the 406); `docs_search` raises the 406. Substrate
down → `request to 127.0.0.1 failed after retries: [Errno 111] Connection refused`.

**Part 3 (Accept + SSE shim, client unmodified):** valid calls work; `isError` results are
mis-handled — `_call_tool` raises a misleading `returned unparsable content` (the error text is
not JSON), and `_call_tool_text` **returns the error text as if it succeeded** (this is the code
path behind `graph_release` / `graph_complete`).

**(b) `probe_sdk.py`:**

| Case | Prediction |
|---|---|
| S01 `auto` | wire: `POST server/discover → 400` (unsupported 2026-07-28), `POST initialize → 200 SSE`, `POST notifications/initialized → 202`, then `tools/list`/`tools/call → 200 SSE`; `protocol_version == "2025-11-25"`; 12 tools; `memory_brief`, `graph_get(dummy)` `is_error=False`; `graph_get {}` and `no_such_tool` `is_error=True` (no exception) |
| S02 `legacy` | same without the discover round trip |
| S03 pinned `2026-07-28` | connects without traffic, then `list_tools`/`call_tool` raise `MCPError(-32000, "Bad Request: Unsupported protocol version …")` |
| S04 / S05 bogus / no bearer | 7410: works (anonymous). Token server: discover 401 → fallback initialize 401 → `MCPError(-32603, "Server returned an error response")` at connect; the 401 is not named |
| S06 / S07 wrong path | 404 non-JSON-RPC body → `MCPError(-32601, "Not Found")` at connect |
| S08 substrate down | connect error (`httpx2.ConnectError`, possibly inside an `ExceptionGroup`) at connect |

## Investigation Trail

1. **Source first.** Read `client.py`, `http.py`, `server.ts`, `mcp.ts`, `config.ts`, and the
   exact TS SDK 1.30.1 transport the server loads. The `Accept` check
   (`webStandardStreamableHttp.js` `handlePostRequest`) predicts a 406 for Omes's shape before
   anything else is evaluated; the stateless transport means `initialize` is *not* required,
   so the 406 and the SSE framing are the only two blockers for the raw shape.
2. **Surprise: `isError` is swallowed even after a fix.** `McpServer` turns *all* tool failures,
   including unknown tool names and schema-validation failures, into `isError: true` results.
   Omes's `_tool_text` ignores `isError`, so fixing `Accept` + SSE alone would make
   `_call_tool_text` (graph_release/graph_complete) report failures as success. Part 3 of the
   probe tests exactly this with a shim, leaving the client untouched.
3. **Surprise: SDK v2 speaks 2026-07-28 first.** `mcp` 2.3.0 defaults to `mode="auto"`, which
   probes `server/discover` with `MCP-Protocol-Version: 2026-07-28`. The TS 1.30.1 server
   rejects that header with a 400 JSON-RPC error *before* method dispatch; the Python client
   lifts that body into an `MCPError(-32000)` and falls back to `initialize`. S01 vs S02 measure
   the cost of that extra round trip, and S03 shows that pinning the modern version breaks.
4. **Auth edge.** The running server has no `SUBSTRATE_TOKEN_*` (the observed `/healthz`
   answered 503, not 401, without any `Authorization` header), so a token-mode server is needed to
   observe the 401 path; `run_token_server.sh` provides one with a scrubbed env. Predicted SDK
   behaviour there: the 401 body is not JSON-RPC, so the error surfaces as a generic `-32603`.
5. **Execution ownership.** Per Main's scope correction, Main runs both probes; the only
   request this spike's author sent to 7410 was the read-only `GET /healthz` recorded below.

## Results

**Verdict: VALIDATED** (Main executed both probes on 2026-10-07 against the running anonymous substrate on 127.0.0.1:7410, plus a token-auth leg on a scrubbed-env server on 127.0.0.1:17411 that was stopped afterwards; `ss` shows 17411 closed.)

**The current Omes client cannot talk to substrate MCP.**
- The exact `SubstrateClient._mcp_post` shape returns **HTTP 406**. Case A02: no `Accept` header. A03/A04: a single media type. In the client, every `_call_tool` and `docs_search` call (B03, B04, B06) raises `HTTP 406`.
- `memory_search` is fail-open, so it silently returns `[]` (B05). The failure is invisible.
- With `Accept: application/json, text/event-stream` the server answers **200 `text/event-stream`** (A05–A10). It works even without `initialize`, because the server is stateless.
- Feeding those real SSE replies through a shim into the unmodified client shows two defects:
  - `_call_tool` cannot parse SSE (C01/C03: "unparsable content").
  - `_call_tool_text` returns the server's **isError** text as a normal string (C04/C05). Tool errors read as success.

**The installed MCP Python SDK (mcp 2.3.0, `streamable_http_client`) works.**
- `mode=auto` (S01) and `mode=legacy` (S02) negotiate protocol **2025-11-25**.
  - Anonymous: 9 tools. With a valid bearer: 12 tools.
  - `CallToolResult.is_error` is **True** for `graph_get {}` and for an unknown tool, and **False** for valid calls.
- `auto` first probes `server/discover` at 2026-07-28, gets 400, and falls back cleanly. Pinning `2026-07-28` (S03) fails: "Unsupported protocol version" (supported: 2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05).
- Token leg: bogus or missing bearer gets 401 at connect (S04/S05); the valid token connects. Wrong path (`/mcp/`, `/`) gets 404, and a closed port fails at connect (S06–S08).

**Signal for the build.**
- Replace the hand-rolled MCP POST with the SDK Streamable HTTP client, in `auto` or `legacy` mode, with a bearer token from the credential broker.
- Treat `is_error` as a failure.
- Keep the REST `/brief` and `/events` calls, which work.
- Surface fail-open results with an explicit reason, instead of returning `[]` silently.

Evidence: `results-omes-shape.json`, `results-sdk.json`, `results-omes-shape-token.json`, `results-sdk-token.json`.
