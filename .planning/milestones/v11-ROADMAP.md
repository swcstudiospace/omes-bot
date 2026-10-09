# Roadmap: v11 Grok Bot native (archived)

Archived 2026-10-09 at milestone close. Phase directories live in
`milestones/v11-phases/`; the milestone audit is `milestones/../../v11-MILESTONE-AUDIT.md`
(at the time of archiving `.planning/v11-MILESTONE-AUDIT.md`) and requirements are
`milestones/v11-REQUIREMENTS.md`.

## Milestone summary

- ✅ **v11 Grok Bot native** — Phases 62-63 (shipped 2026-10-09; audit passed 17/17)

Omega Prime becomes a production-grade, enterprise-ready Grok Bot tool host with a
one-command install. Source plan: ultrathink graph `ut-mv0nfl17-58362dc4` (Linear
SPE-8895..SPE-8900), translated from its stack-agnostic wording to this Python MCP host.
User direction (2026-10-09): push to `main` with `prime-agent` as a git submodule.

- [x] **Phase 62: Grok Bot native runtime completion** - Bootstrap/config, health, lifecycle and transport components finished and proven over a real socket.
- [x] **Phase 63: Seven enterprise improvements** - Streamable HTTP, scoped credentials, approval gateway, traffic protection, observability, live verifier, deployment kit.

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

- [x] 63-01: Streamable HTTP transport (GRI-01)
- [x] 63-02: Scoped, rotatable credentials + token CLI (GRI-02)
- [x] 63-03: Human approval gateway (GRI-03)
- [x] 63-04: Traffic protection - rate limits + circuit breaker (GRI-04)
- [x] 63-05: Observability - metrics, trace context, NDJSON logs (GRI-05)
- [x] 63-06: Live conformance verifier, served manifest + launcher self-test (GRI-06)
- [x] 63-07: Deployment kit + image CI (GRI-07)
- [x] 63-08: Integration wiring, docs, milestone audit
