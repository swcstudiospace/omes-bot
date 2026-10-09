---
milestone: v11
name: Grok Bot native
audited: 2026-10-09
status: passed
scores:
  requirements: 17/17
  phases: 2/2
  plans: 14/14
requirement_disposition: all-wired
active_phase: none
open: []
exceptions: []
---

# v11 milestone audit: passed

**Scope.** Make the one-command Grok Bot attachment production-grade and enterprise-ready: finish the shipped
`omega_prime/grokbot/` runtime (Phase 62), then add seven improvements (Phase 63). The source plan was the
ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900); the planner could not see this repo, so its
TypeScript layout was translated onto the Python MCP host. User direction (2026-10-09): push to `main` with
`prime-agent` as a git submodule.

**Result.** 17/17 requirements satisfied, none through an exception. Every claim below was exercised on a real process,
a real socket or the real image, not only in-process tests. Evidence is in `62-VERIFICATION.md` and
`63-VERIFICATION.md`; this audit maps requirements to it.

## Requirement-by-requirement

| Requirement | Wired through | Status | Evidence |
|---|---|---|---|
| GRK-01 Auth fails closed | `security.py` (`TokenStore`, `AuthMiddleware`, `check_bind_safety`) | WIRED | Header-only bearer; `?token=` is 401; constant-time digest compare; non-loopback bind without a credential exits 2 (live) |
| GRK-02 Browser-origin safety | SDK `TransportSecuritySettings`, `_OriginGuard`, named-origin CORS | WIRED | Hostile Origin 403 on a real process; no `*`; Host validation per bind |
| GRK-03 Startup fails closed | `load_runtime`, `serve_sse` exit 2 | WIRED | Broken roster, policy, approval and token-file permission cases exit 2 on both transports |
| GRK-04 Truthful health | `/healthz`, `/readyz` | WIRED | Tool count equals the served tools (108); 503 while draining, with an unwritable audit log or an unreadable token store |
| GRK-05 Tamper-evident audit | `audit.py`, `AuditInterceptor` | WIRED | Hash chain, rotation, quarantine; edit/removal/reorder detected; verified inside the container; scope denials recorded (fixed in review) |
| GRK-06 Truthful manifest | `manifest.py`, `lint_template`, `/manifest.json` | WIRED | Served and approval-gated tools, config-derived capabilities, digest; no token value; sync reports no false drift |
| GRK-07 Strict launcher | `oneclick.py` | WIRED | Exit 3 on failed preflight, 2 on unsafe bind; `--generate-token` shows once and writes 0600; `--dry-run` serves nothing; real launch observed |
| GRK-08 Graceful lifecycle | `GracefulServer`, `supervisor.py` | WIRED | SIGTERM exits 0 in ~1 s with `/readyz` 503 while draining; `docker stop` exit 0 in 1.3 s; supervisor `--stop` stops its child |
| GRK-09 Correct tooling | `sync.py`, `doctor.py` (15 checks), `emulator.py` | WIRED | Emulator drives the production runtime (roster, policy, approvals, scopes, audit) |
| GRK-10 Proof over a real transport | `test_grokbot_e2e.py`, `test_grokbot_integration.py` | WIRED | MCP SDK client over a uvicorn socket: initialize, list, call, 401, Origin, audit |
| GRI-01 Streamable HTTP | `streamable.py`, `/mcp` | WIRED | Listed and called 108 tools over `/mcp` and `/sse` on a live host; foreign session id is 404 |
| GRI-02 Scoped credentials | `tokens.py` | WIRED | Revoked token 401 on the next request, no restart; expiry via injected clock; corrupt file denies everyone |
| GRI-03 Approval gateway | `approvals.py`, `approvals_api.py` | WIRED | `call` token 403, admin 201 with TTL; gated tool passed its gate; audited with the approver principal |
| GRI-04 Traffic protection | `ratelimit.py`, `resilience.py` | WIRED | 429 with `Retry-After`, auth-failure throttle, breaker open and recovery; denials audited and counted |
| GRI-05 Observability | `metrics.py`, `telemetry.py` | WIRED | `/metrics` series, request id and `traceparent` on every response, NDJSON logs (36/36 lines in the container), no token text |
| GRI-06 Live verifier | `verify.py`, `oneclick --self-test` | WIRED | 22 checks pass on a good host, exit 1 on an unsafe one, exit 2 unreachable; 20 pass inside the final container |
| GRI-07 Deployment kit | `deploy.py`, `Dockerfile`, image workflow | WIRED | Zero findings on all four targets; `docker build --check` clean; real hardened container run; Trivy 0 vulnerabilities |

## CI

On `d684f5e`: `ci` 10/10 (Python 3.12, 3.13, 3.14), `supply-chain`, and `grokbot-image` on its first run (image build,
hardened boot, in-container verifier, `docker stop` exit 0, SBOM, vulnerability scan) all succeeded. `main` was red before
this milestone.

## Integration and flows

- **Single path.** One `create_sse_app` composes auth, throttles, observers, denying interceptors and both transports;
  one `ToolGate` serializes tool calls across `/sse` and `/mcp`; the same `Runtime` feeds `/healthz`, `/manifest.json`
  and `tools/list`, so the three agree (108).
- **Flows exercised end to end on a real process:** launch, authenticate with three scopes, list and call over both
  transports, refuse a read-only caller, approve with a TTL, revoke a token, scrape metrics, drain on SIGTERM, verify the
  audit chain.

## Defects found by the audit itself (all fixed)

Event-loop blocking tool calls; a token leaking into uvicorn's access log; scope denials missing from the audit log; mixed
text and JSON log lines; test-order dependent logging; a CI image scan that would have failed on third-party dataset false
positives; a race in a scheduler test widened by the (correct) atomic job-store write. Pre-existing breakage on `main`
repaired along the way: an uninstallable `requirements-lock.txt` (merged Dependabot majors) and a non-atomic job store.
Details and evidence: `62-VERIFICATION.md`, `63-VERIFICATION.md`.

## Decisions recorded (2026-10-09)

- Static scoped bearer tokens replace the graph's HMAC-signed webhook ingress: Grok Bot reaches this host as an MCP client.
- Per-principal scopes replace the graph's per-tenant sandbox: Omega Prime is a single seat.
- Dependabot ignores the `oauthlib` and `huggingface-hub` major bumps until `tweepy` and `tokenizers` relax their pins.
- Default rate limits are generous (600 requests/min, 300 tool calls/min per principal): they stop runaways, not coding agents.

## Open items and next safe actions

- **None block the milestone.** Not exercised: a live Kubernetes apply, a started systemd unit, and Python 3.13/3.14 locally
  (CI covers 3.12-3.14).
- **Archive and cleanup are not done.** Moving `.planning/phases/6[23]-*` into `milestones/v11-phases/` and collapsing the
  roadmap follows the same rule recorded for v10 (separate user confirmation before moving phase directories). Everything
  needed for it is in place: summaries and verification for all 14 plans, this audit, and a clean tree.
- Open Dependabot PRs for `oauthlib` 4 and `huggingface-hub` 2 are obsolete with the new ignore rules and can be closed.
