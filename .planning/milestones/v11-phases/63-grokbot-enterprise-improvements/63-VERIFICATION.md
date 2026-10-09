---
phase: 63-grokbot-enterprise-improvements
verified: 2026-10-09
status: passed
score: 8/8 plans verified, 7/7 requirements satisfied
gaps: []
---

# Verification: Phase 63 Seven enterprise improvements

**Status:** passed
**Date:** 2026-10-09
**Commits:** `90ce880` through `d684f5e` on `main` (the improvements, the integration, the verifier, the docs and the CI and test repairs). The `prime-agent` submodule stays pinned at `967eb13f`.

## The seven improvements

1. Streamable HTTP at `/mcp` next to legacy SSE.
2. Scoped, expiring, revocable credentials (`read` / `call` / `admin`) in a hashed token file with a CLI.
3. A human approval gateway (`/admin/approvals`) with TTL, revoke and audit.
4. Traffic protection: per-principal and global rate limits, an auth-failure throttle, a per-tool circuit breaker.
5. Observability: Prometheus `/metrics`, request ids and `traceparent`, structured NDJSON logs, a no-query-string access log.
6. A live conformance verifier (`python -m omega_prime.grokbot.verify`) and `oneclick --self-test`.
7. A deployment kit: a hardened image, Docker/Compose/systemd/Kubernetes renderers, a hardening checker, an image CI workflow.

## Success criteria

1. An MCP client connects over Streamable HTTP and over legacy SSE with the same auth, origin and audit behavior - PASS. On a real process both listed 108 tools and called one with a scoped `call` token; the audit log labels the transports; `test_grokbot_integration.py` covers both over a real socket.
2. A revoked or expired token stops working without a restart; a `call` token cannot reach `/admin/*`; an admin can approve a gated tool with a TTL, both audited - PASS. Live: revoked token 401 on the next request; `call` token 403; admin 201 with `expires_at`; the gated tool then passed the approval gate (rejected only for missing arguments, so nothing ran); audit shows `approval_granted` by the admin principal.
3. A burst beyond the limit gets 429 with `Retry-After`; repeated infrastructure failures open a breaker that recovers - PASS in the integration suite (injected clocks, real socket): 429 with a whole-second `Retry-After`, auth-failure throttle, `circuit_open` without running the tool, recovery after the cooldown.
4. `/metrics` exposes request, tool-call, auth-failure and latency series; responses and audit records carry the request id; `--log-format json` emits redacted NDJSON - PASS. Live: `/metrics` 401 without a token and HTTP series with one; `X-Request-Id` and `traceparent` on every response; in the final container all 36 log lines were valid JSON; the token appeared 0 times in logs or the audit file.
5. The verifier passes against a freshly started host over both transports and fails against a misconfigured one - PASS. A configured host: 22 checks pass, exit 0. A host with authentication off plus `--require-auth`: exit 1. An unreachable URL: exit 2. Inside the final container, as CI runs it: 20 pass, exit 0.
6. `deploy render` output for all four targets parses and passes the hardening checks; `docker build --check` accepts the Dockerfile - PASS. Zero findings on every target; `docker build --check .` "no warnings found"; `actionlint` clean on all workflows.
7. Full suite, evals, assemble check, catalog check, docs tests, `ruff`, `mypy` pass - PASS (see receipts).

## Requirement coverage

| ID | Evidence |
|---|---|
| GRI-01 | `streamable.py`; `test_grokbot_streamable.py` (13), `test_grokbot_integration.py`; live `/mcp` call |
| GRI-02 | `tokens.py`; `test_grokbot_tokens.py` (23), integration revoke/expiry; live revoke without restart |
| GRI-03 | `approvals.py` TTL + `approvals_api.py`; `test_approvals_ttl.py`, `test_grokbot_approvals_api.py` (43); live 403 vs 201 |
| GRI-04 | `ratelimit.py`, `resilience.py`; 89 tests; integration 429, throttle, breaker recovery |
| GRI-05 | `metrics.py`, `telemetry.py`; 68 tests; live `/metrics`, request ids; container NDJSON |
| GRI-06 | `verify.py`, `oneclick --self-test`; `test_grokbot_verify.py`; live runs above |
| GRI-07 | `deploy.py`, `Dockerfile`, workflow; `test_grokbot_deploy.py`; real image run, `docker stop` exit 0 in 1.3 s |

## The image, verified for real

Built from the committed `Dockerfile` (1.99 GB: the dependency tree includes PyRIT and transformers). Run with the CI workflow's flags: `--read-only --tmpfs /tmp --tmpfs /var/lib/omega-prime --cap-drop ALL --security-opt no-new-privileges`, uid 10001, the token mounted from a 0600 file. `/healthz` and `/readyz` 200; `/sse` 401 without a token and for `?token=`; the root filesystem rejects writes; a real MCP client lists 108 tools; a `memory` write lands in the state volume and not in the source package; the audit log inside the container verifies; `docker stop` exits 0 in 1.3 s. Trivy (`--scanners vuln --severity CRITICAL --ignore-unfixed`) exits 0: 0 vulnerabilities in the Debian base and in all 146 pinned Python packages.

## Found and fixed during verification

- **Scope denials were not audited.** `run_tool_call` stops at the first denial and runs `after` only for interceptors whose `before` ran, so with the order InFlight, Scope, Audit a read-only token's denied call left no audit record (experiment: `audit events=[]`). Audit and metrics now precede every denying interceptor; an E2E test and the live run show the `denied`/`forbidden` record and the metric.
- **Test-order dependent logging failures.** `configure_logging` sets `propagate=False` on the `omega_prime` logger; a test that started a host left that state behind, so pytest attached its capture handlers there. An autouse fixture now restores `omega_prime`, `omega_prime.access` and `uvicorn.access` around every test.
- **Mixed plain-text and JSON log lines** (33 of 44 were JSON): uvicorn's own records and the launch banner now follow `--log-format json`; uvicorn's ANSI `color_message` is dropped.
- **CI image scan would have failed on false positives:** Trivy's secret scanner flagged PyRIT's own red-team privacy datasets. The scan is `scanners: vuln`.
- **A scheduler test raced the store's second write** (waited for the runner call, then read the result). The atomic save from Phase 62's repair is slower than a bare write and widened the window. The tests wait for completion and the persisted result; 14 consecutive runs pass.
- **Default limits were too tight for a coding agent** (60 tool calls/min): 600 requests/min and 300 tool calls/min per principal now stop runaway clients without throttling normal use.
- **Pyright findings mypy cannot see** (anyio `to_thread` resolution, an `@asynccontextmanager` annotated `-> Any`, `uvicorn.config`): fixed, not suppressed.

## Receipts

- `pytest omega_prime/tests` -> 753 + 37 + 1003 = 1793 passed in three chunks (the harness caps a command near 60 s), 0 failed.
- `python -m omega_prime.evals.runner omega_prime/evals/cases` -> exit 0, 26 passed.
- `assemble-prompts.sh --check`, `catalog --check`, `setup_check --root .` -> exit 0.
- `ruff check` and `ruff format --check omega_prime/` -> exit 0; `mypy omega_prime/` -> exit 0 (294 files); `pyright` on `mcp_server.py`, `omega_prime/grokbot`, `approvals.py`, `scheduler.py` and the new tests -> 0 errors.
- `actionlint` -> exit 0; `docker build --check .` -> "no warnings found".
- Documentation: 103 command flags in the docs' code blocks were checked against the real `--help` output; none is missing (4 apparent misses were flags of the supervised `mcp_server` command inside the supervisor example).
- `pip-audit -r requirements-lock.txt --ignore-vuln PYSEC-2026-4114` -> "No known vulnerabilities found, 1 ignored".
- CI on `d684f5e` (GitHub Actions, all green): `ci` 10/10 jobs (`verify`, `lint` and `types` on Python 3.12, 3.13 and 3.14, plus `docs`); `supply-chain` (`pip-audit`); `grokbot-image` on its first run, every step: build the image, boot it with the hardened flags, wait for the healthcheck, run `python -m omega_prime.grokbot.verify` inside the container, `docker stop` with exit code 0, SBOM, Trivy scan; Dependabot's `pip`, `github_actions` and the new `docker` ecosystem runs. Before this work `main` was red (`supply-chain` failed on 4 of 5 merges and `ci` on the last).

## Known limitations

- The Kubernetes manifest was not applied to a cluster and the systemd unit was not started (`systemd-analyze verify` only reports the missing binary).
- Credentials are static scoped bearer tokens, not OAuth. One seat; tools run one at a time. The approval log is in memory (a restart drops runtime grants; startup `--approve` flags are re-applied).
- The image is about 2 GB. Runtime skill creation needs a writable skills volume (skills stay under the read-only root).
- `generate_manifest(env=...)` overlays Prime flags for `capabilities` only; `default_registry` reads flags from `os.environ`.
- Python 3.13 and 3.14 were not run locally (3.12 only); the CI matrix covers them.
