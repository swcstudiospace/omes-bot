# Phase 63: Seven enterprise improvements - Context

**Gathered:** 2026-10-09
**Status:** Design fixed; unit plans are written against the final Phase 62 code
**Mode:** Orchestrated. Source plan: ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900), translated to this Python MCP host.

<domain>
## The seven improvements (suggested, then programmed)

Each is additive to the Phase 62 baseline and grounded in a real gap found while auditing the host.
The right-hand column is the graph's own candidate it comes from.

| # | Improvement | Why it is needed here | Graph candidate |
|---|---|---|---|
| 1 | **Streamable HTTP** at `/mcp` next to legacy SSE | SSE-only is the deprecated MCP transport; current MCP clients and gateways expect Streamable HTTP | Stream engine + backpressure (bounded sessions, idle timeout, body limit, disconnect cleanup) |
| 2 | **Scoped, rotatable credentials** (`read`/`call`/`admin`, hashed 0600 token file, CLI, live reload, fail-closed) | One shared env token cannot be rotated, scoped or attributed; audit needs a per-caller identity | Ingress security + tenant isolation (per-principal scopes, single seat) |
| 3 | **Human approval gateway** (`/admin/approvals`, TTL, revoke, audited) | Approval-gated tools (deploys, publishes, merges) can only be approved by restarting the host with `--approve` | Tenant sandbox / governance |
| 4 | **Traffic protection**: two-tier rate limits, auth-failure throttle, per-tool circuit breaker | Nothing stops a runaway client or a brute-force attempt, and a failing upstream is hammered | Circuit breaker + two-tier token bucket |
| 5 | **Observability**: Prometheus `/metrics`, W3C `traceparent` + request id everywhere, NDJSON logs | No metrics, no correlation id, free-text logs | Correlated telemetry |
| 6 | **Live conformance verifier**: host serves `/manifest.json`; `verify` drives a real MCP client over both transports; `oneclick --self-test` proves graceful SIGTERM | "1-click works" is only a claim until a client proves it end to end | Startup health handshake + lifecycle teardown |
| 7 | **Deployment kit**: Docker, compose, systemd, Kubernetes renderer + hardening check + image CI (build, scan, SBOM) | Enterprises deploy containers or units, not `python -m` commands | Atomic state / production hardening |
</domain>

<decisions>
## Decisions

- No new third-party dependencies (Prometheus text, token store, YAML templates are hand-written; PyYAML is only
  used in tests and is already present transitively).
- `--token-file` (Phase 62) stays "one plaintext token in a 0600 file". The multi-token hashed JSON store is
  `--token-store PATH`, managed by `python -m omega_prime.grokbot.tokens`.
- A token store that cannot be read or parsed denies everyone (fail closed); `/readyz` reports it degraded.
- The approvals API and the admin scope exist only when authentication is enabled; with auth disabled the
  `/admin/*` routes are not mounted at all.
- Two `mcp.server.Server` instances (one labelled `sse`, one `http`) share one registry, one interceptor list and one
  `ToolGate` (so calls stay serialized across both transports) while audit and metrics can tell the transports apart.
- All middleware is pure ASGI; order outermost-first: request context, metrics, CORS (only if origins),
  auth-failure throttle, auth, request rate limit.
- Metrics labels are bounded: path groups (`/sse`, `/messages`, `/mcp`, `/healthz`, `/readyz`, `/metrics`,
  `/manifest.json`, `/admin`, `other`) and tool names only when they are in the served list (else `unknown`).
- Interceptor order for tool calls: `InFlight`, `Scope`, `ToolRateLimit`, `CircuitBreaker`, `Metrics`, `Audit`.
- Every limit is configurable and `0` disables it.
- Tool calls run in a worker thread behind one shared `ToolGate` (Phase 62; serial by default). Interceptors therefore
  run off the event loop: every interceptor and every structure it shares (rate limiter, breaker map, metrics
  registry, approval log) must be thread-safe and must not hold loop-bound state.
</decisions>

<contracts>
## Module contracts (signatures are binding; add optional keyword arguments only)

Phase 62 modules these build on: `security.py` (`Principal`, `TokenStore`, `AuthMiddleware`,
`principal_from_scope/request`, scopes), `interceptors.py` (`ToolCall`, `ToolDenial`, `ToolOutcome`,
`ToolCallInterceptor`, `run_tool_call`), `audit.py` (`GrokBotAuditTracer.log_event`), `_io.py`,
`remote.create_sse_app/serve_sse`, `mcp_server.load_runtime/build_server`.

### streamable.py (63-01)
```python
@dataclass
class StreamableHttp:
    manager: StreamableHTTPSessionManager
    route: Route                       # Route("/mcp", <ASGI endpoint>, methods=["GET","POST","DELETE"])
    def lifespan(self) -> AbstractAsyncContextManager[None]     # `async with manager.run()`
def build_streamable_http(server, *, security_settings=None, max_body_bytes=1_048_576, max_sessions=64,
                          session_idle_timeout=1800.0, json_response=False) -> StreamableHttp
```
A session is bound to the principal that created it: a request carrying an `Mcp-Session-Id` created by a
different principal id gets 403 (use the SDK's session-owner mechanism if it can be fed from our principal;
otherwise a thin wrapper recording `session id -> principal id` from the response header).

### tokens.py (63-02)
```python
class FileTokenStore(TokenStore):     # subclass: AuthMiddleware needs no change
    def __init__(self, path, *, clock=time.time, reload_interval=1.0)
    # enabled -> True once configured (even when degraded). verify(): stat() at most once per
    # reload_interval; reload when mtime/size changed; expired (expires_at) or revoked tokens -> None;
    # unreadable/corrupt file -> deny all and `degraded` is True with `degraded_reason`.
    degraded: bool; degraded_reason: str | None
class CompositeTokenStore(TokenStore): def __init__(self, stores: Sequence[TokenStore])  # first match wins
def create_token(path, *, scopes, label="", ttl_days=None, clock=...) -> tuple[str, TokenRecord]  # plaintext returned once
def list_tokens(path) -> list[TokenRecord]; def revoke_token(path, token_id) -> bool
def main(argv=None) -> int      # new --file F [--scope S ...] [--label L] [--ttl-days N] | list --file F | revoke --file F ID
```
File format `{"version": 1, "tokens": [{"id", "sha256", "scopes", "label", "created_at", "expires_at", "revoked_at"}]}`,
written with `atomic_write_json` (0600). Token ids are `tok_` + 8 hex.

### approvals (63-03)
`omega_prime/tools/approvals.py` `ApprovalLog` gains, all backward compatible:
`__init__(self, *, clock=time.time)`, `approve(..., ttl_seconds: float | None = None)` (adds `expires_at`
to the returned dict when a TTL is given), `revoke(tool) -> bool`, `entries() -> list[dict]`
(`tool`, `approved_by`, `approved_at`, `expires_at`), and `is_approved` honors expiry.
`omega_prime/grokbot/approvals_api.py`:
```python
def approval_routes(*, approval_log, gated_tools: Callable[[], Sequence[str]], audit=None,
                    default_ttl_seconds=3600.0, max_ttl_seconds=86400.0) -> list[Route]
# GET /admin/approvals  POST /admin/approvals {"tool": str, "ttl_seconds": number?}  DELETE /admin/approvals/{tool}
# Every handler requires principal.allows("admin") (401 without a principal, 403 otherwise); the tool must be in
# gated_tools() (404 otherwise); approver = principal.label or principal.id (never the bot); body size <= 4096;
# audit events approval_granted / approval_revoked (details: tool, ttl, approver); responses never echo secrets.
```

### ratelimit.py, resilience.py (63-04)
```python
class RateLimiter:                      # token bucket per key + one global bucket; clock injectable
    def __init__(self, per_key_per_minute: int, global_per_minute: int = 0, *, burst: int | None = None, clock=time.monotonic)
    def acquire(self, key: str) -> float | None      # None = allowed, else seconds to wait (Retry-After)
class RateLimitMiddleware:              # pure ASGI, after auth; key = principal id else client host; exempt /healthz /readyz
    def __init__(self, app, *, limiter: RateLimiter, exempt_paths=("/healthz", "/readyz"), on_limited=None)
class AuthFailureThrottle:              # per-client failures in a sliding window
    def __init__(self, max_failures: int, window_seconds: float = 60.0, *, clock=time.monotonic)
    def record(self, client: str) -> None; def blocked(self, client: str) -> float | None
class AuthThrottleMiddleware:           # pure ASGI, BEFORE auth: 429 + Retry-After when blocked(client)
class ToolRateLimitInterceptor:         # before(): limiter.acquire(principal id or "local") -> ToolDenial("rate_limited", ..., retry_after)
class CircuitBreaker:                   # closed/open/half_open; failure_threshold, cooldown, jitter, clock, rng
class ToolCircuitBreakerInterceptor:    # one breaker per tool name; denial code "circuit_open"
def is_infrastructure_failure(error: str | None) -> bool
```
`is_infrastructure_failure` is True only for transient/upstream failures (inspect `omega_prime/tools/*` for the
error prefixes tools actually emit, e.g. `upstream_error:`, timeouts, connection failures); it is False for policy,
approval, validation, `not_configured`, `rate_limited` and `circuit_open` results so caller mistakes never open a breaker.

### metrics.py, telemetry.py (63-05)
```python
class MetricsRegistry: counter(name, help, labels=()), gauge(...), histogram(name, help, labels=(), buckets=DEFAULT), render() -> str
    # each returns an object with .labels(**kw).inc()/.set()/.observe(); thread-safe; Prometheus text format 0.0.4 with escaping
class MetricsMiddleware: pure ASGI; http requests total/duration/in-flight by method, path group, status class
class MetricsInterceptor: tool calls total/duration/in-flight by tool and status; denials by code
def metrics_endpoint(registry, *, required_scope="read") -> ASGI endpoint     # 401/403 per principal; text/plain; version=0.0.4
def record_auth_failure(registry) -> Callable[[dict], None]                     # for AuthMiddleware.on_failure
def parse_traceparent(value) -> TraceContext | None ; def new_trace_context(parent=None) -> TraceContext
class RequestContextMiddleware: pure ASGI; sets scope["state"]["request_id"] and ["trace"]; response headers
    `X-Request-Id` and `traceparent`; a malformed inbound traceparent is replaced, never echoed
class JsonLogFormatter(logging.Formatter)       # NDJSON, redaction via audit.redact_sensitive
def configure_logging(fmt="text", level="INFO") -> None
class AccessLogMiddleware: one record per request on logger "omega_prime.access" (no query string, no headers)
```

### remote.py integration (63-08, one owner)
`create_sse_app` gains keyword arguments: `token_store_path`, `rate_limit`, `tool_rate_limit`,
`global_rate_limit`, `auth_failure_limit`, `breaker_threshold`, `breaker_cooldown`, `metrics_enabled`,
`metrics_scope`, `log_format`, `session_idle_timeout`, `max_sessions`, `approval_max_ttl`. New routes:
`/mcp` (Streamable HTTP), `/metrics`, `/manifest.json` (read scope; manifest generated once for the
effective settings and cached), `/admin/approvals` (only when auth is enabled). `/readyz` adds
`token_store` and `streamable_http` checks. `mcp_server.main` gains the matching flags; `--token-store PATH`.

### verify.py (63-06), deploy.py (63-07)
`verify.run_verification(base_url, *, token=None, admin_token=None, transports=("sse", "http"), gated_tool=None,
timeout=10.0) -> VerifyReport` (`checks[{id,title,status pass|fail|skip,detail,duration_ms}]`, `ok`);
CLI `python -m omega_prime.grokbot.verify --url URL [--token-env N | --token-file F] [--json]` exits 0/1.
`oneclick --self-test` launches a host subprocess on a free port with a generated token, runs the verifier,
sends SIGTERM and requires exit code 0 within the grace period.
`deploy.render(target, out_dir, *, name="omega-prime-mcp", image=..., port=8000, public_url=None) -> list[Path]`;
`deploy.check(out_dir) -> list[Finding]`; CLI `python -m omega_prime.grokbot.deploy render|check`.
</contracts>

<conventions>
Same as Phase 62 (`62-CONTEXT.md` `<conventions>`): header lines, no dependencies, no running gates inside units,
hermetic tests, mypy/ruff clean, existing tests stay valid.
</conventions>
