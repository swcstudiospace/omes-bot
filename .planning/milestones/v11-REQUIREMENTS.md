# Requirements: Omega Prime v11 Grok Bot native

**Defined:** 2026-10-09
**Core Value:** One command attaches Omega Prime to Grok Bot as a hardened,
observable, verifiable tool host - production-grade and enterprise-ready,
with every claim in its manifest and docs backed by a command and an exit code.

Source plan: ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900),
translated from its stack-agnostic wording to this Python MCP host. Evidence for
Phase 62 is the defect inventory in `.planning/phases/62-grokbot-native-runtime/62-CONTEXT.md`.
The v10 requirements are archived in `milestones/v10-REQUIREMENTS.md`.

## v11 Requirements

### Runtime completion (Phase 62)

- [x] **GRK-01**: Remote auth fails closed. Bearer tokens are verified in constant time from
  the `Authorization` header only; `?token=` is rejected; a missing or invalid token gets
  401 with `WWW-Authenticate: Bearer`; the server refuses to start on a non-loopback bind
  without a token unless `--allow-insecure-no-auth` is given
- [x] **GRK-02**: Browser-origin safety. Host/Origin validation uses the MCP SDK transport
  security (loopback names, public URL, explicit allow-lists); CORS is emitted only for
  explicitly allowed origins (no wildcard, no duplicate stack); request-body and session
  limits come from configuration
- [x] **GRK-03**: Startup fails closed. An unreadable or invalid seat policy, roster, token
  file, or `--approve` entry exits 2 with a one-line reason on both transports;
  `--approve` is honored on the remote transport
- [x] **GRK-04**: Health is truthful. `/healthz` reports the version and the number of tools
  actually served; `/readyz` is 503 until startup checks pass and again once shutdown begins
- [x] **GRK-05**: Audit is wired and tamper-evident. Every remote `tools/call` and auth
  failure is appended to a hash-chained, size-rotated, 0600 log with the principal,
  argument key names and an argument digest (never raw secrets);
  `python -m omega_prime.grokbot.audit verify` detects edits, deletions and reordering
- [x] **GRK-06**: The manifest is truthful. `tools` equals what the host serves for the same
  settings; `approval_required` lists gated tools; capabilities derive from configuration;
  it carries the public URL (never `0.0.0.0`), the version and a content digest; no token is
  ever written; every skill and routine the template names exists on disk (lint)
- [x] **GRK-07**: The 1-click launcher is strict. A failing preflight aborts with exit 3
  unless `--no-strict`; secrets come from env or a 0600 file (an argv token warns);
  `--generate-token` mints a token shown once; `--dry-run` runs preflight, manifest and
  bind-safety and exits 0 without serving
- [x] **GRK-08**: Lifecycle is graceful. SIGTERM/SIGINT drain in-flight tool calls within a
  grace period, flush the audit log and exit 0; the supervisor's `--stop` stops the
  supervisor and its child, probes `/healthz`, resets its restart budget after stable
  uptime, writes state atomically and exits non-zero when it gives up
- [x] **GRK-09**: Tooling is correct. `sync --check` reports drift only for content Grok Bot
  would see; `doctor` adds policy, roster, token, template and audit-chain checks and honors
  the configured host; the emulator drives the same runtime (policy, approvals,
  interceptors) the server uses
- [x] **GRK-10**: Proof over a real transport. At least one test serves the ASGI app on a
  socket and drives it with the MCP client (initialize, list tools, call a tool, 401 and
  Origin rejections, audit record written)

### Enterprise improvements (Phase 63)

- [x] **GRI-01**: Streamable HTTP. The same app serves MCP Streamable HTTP at `/mcp`
  (stateful sessions, SDK security settings) next to legacy SSE; both obey the same auth,
  origin, limit and audit rules
- [x] **GRI-02**: Scoped credentials. Tokens live in a hashed, 0600 token file with ids,
  scopes (`read`, `call`, `admin`) and expiry; `python -m omega_prime.grokbot.tokens
  new|list|revoke` manages them (plaintext shown once, never stored); the server picks up
  changes without a restart, a revoked or expired token stops working immediately, and an
  unreadable token file denies everyone (fail closed)
- [x] **GRI-03**: Approval gateway. An admin-scoped HTTP API (`GET/POST /admin/approvals`,
  `DELETE /admin/approvals/{tool}`) approves gated tools at runtime with a TTL, records the
  approver principal (never the bot) and audits every change; a `call`-scope token cannot
  reach it
- [x] **GRI-04**: Traffic protection. Two-tier token-bucket limits (per principal and
  global) on HTTP requests and on tool calls answer 429 / `rate_limited` with `Retry-After`;
  repeated failed authentication from one client is throttled; a per-tool circuit breaker
  fails fast with `circuit_open` after consecutive infrastructure failures, half-opens with
  jitter and recovers; every limit is configurable and disabled with 0
- [x] **GRI-05**: Observability. Prometheus text at `/metrics` (read scope or above),
  W3C `traceparent` propagation with a request id on every response and audit record, and
  NDJSON structured logs with redaction (`--log-format json`)
- [x] **GRI-06**: Live verifier. The host serves its own truthful manifest at
  `GET /manifest.json` (read scope). `python -m omega_prime.grokbot.verify --url URL` drives a
  real MCP client against a running host over SSE and Streamable HTTP (health and readiness,
  manifest vs `tools/list`, initialize, scoped call, gated-tool refusal, auth and origin
  negatives) and returns JSON plus an exit code; `oneclick --self-test` starts a host, runs
  it, checks the graceful SIGTERM exit and CI runs it
- [x] **GRI-07**: Deployment kit. `python -m omega_prime.grokbot.deploy render --target
  {docker,compose,systemd,k8s}` writes hardened artifacts (non-root, read-only root
  filesystem, healthcheck, SIGTERM grace, resource limits, no inline secrets); a CI workflow
  builds the image, scans it and emits an SBOM

## Out of Scope

| Feature | Reason |
|---------|--------|
| OAuth authorization server for MCP | Static scoped bearer tokens are the supported contract; an AS is a separate product |
| Multi-tenant sandbox / per-tenant stores | Omega Prime is single-seat; each Add-Bot install is its own copy. Per-principal scopes are the isolation unit |
| WebSocket transport | MCP defines stdio and Streamable HTTP; legacy SSE is kept for existing clients |
| Live Grok Bot cloud / xAI account verification | No credentials in the hermetic environment; the verifier proves the wire contract against our own host |
| Merging the open Dependabot major bumps (oauthlib 4, huggingface-hub 2) | Not requested; oauthlib 4 conflicts with the tweepy pin recorded in SECURITY.md |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRK-01 | 62 | Complete |
| GRK-02 | 62 | Complete |
| GRK-03 | 62 | Complete |
| GRK-04 | 62 | Complete |
| GRK-05 | 62 | Complete |
| GRK-06 | 62 | Complete |
| GRK-07 | 62 | Complete |
| GRK-08 | 62 | Complete |
| GRK-09 | 62 | Complete |
| GRK-10 | 62 | Complete |
| GRI-01 | 63 | Complete |
| GRI-02 | 63 | Complete |
| GRI-03 | 63 | Complete |
| GRI-04 | 63 | Complete |
| GRI-05 | 63 | Complete |
| GRI-06 | 63 | Complete |
| GRI-07 | 63 | Complete |

**Coverage:** 17 requirements, 17 mapped, 0 unmapped.
