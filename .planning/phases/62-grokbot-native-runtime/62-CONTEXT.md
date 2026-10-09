# Phase 62: Grok Bot native runtime completion - Context

**Gathered:** 2026-10-09
**Status:** Ready for execution
**Mode:** Orchestrated. Source plan: ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900), translated to this Python MCP host.

<domain>
## Phase Boundary

Finish the four runtime components the plan names, in this repo's terms:

| Plan component | Here |
|---|---|
| Bootstrap and config | `oneclick.py`, config/flag layering, manifest, `sync.py` |
| Health probe | `/healthz`, `/readyz`, `doctor.py` |
| Lifecycle | graceful drain, `supervisor.py` |
| Streaming engine | the SSE host in `remote.py` (bounded, authenticated, audited) |

The shipped package is `omega_prime/grokbot/` (commit 5e4775f) plus the `--transport sse` branch of
`omega_prime/mcp_server.py`. Scope is correctness, security and truthfulness of that code. New
capabilities (Streamable HTTP, credential files, approvals API, rate limits, metrics, verifier,
deployment kit) are Phase 63.
</domain>

<defects>
## Evidence: defects in the shipped code (all verified by reading the source on 2026-10-09)

| ID | File | Defect |
|---|---|---|
| D-01 | remote.py auth_middleware | Token compared with `!=` (not constant time) |
| D-02 | remote.py auth_middleware | Accepts `?token=` query-string credential (leaks into logs and referrers) |
| D-03 | remote.py, mcp_server.py main | No token means a fully open server, even with `--host 0.0.0.0` |
| D-04 | remote.py | `allow_origins=["*"]` and the CORS middleware is added twice; no Origin/Host validation |
| D-05 | remote.py | `except Exception: policy = None` swallows an invalid policy (fail-open) |
| D-06 | remote.py | `/readyz` is always `ready: true`; `/healthz` hard-codes version and a fallback of 108 tools |
| D-07 | remote.py | No body-size or session limits; no graceful drain |
| D-08 | mcp_server.py main | `--approve` is parsed after the SSE branch returns, so it is ignored for remote |
| D-09 | grokbot/audit.py | `GrokBotAuditTracer` is used only by the emulator; remote tool calls are never audited |
| D-10 | remote.py | `BaseHTTPMiddleware` wraps a streaming SSE response (breaks streaming and disconnect handling) |
| D-11 | audit.py | Docstring promises rotation; there is none. Not tamper-evident (verify only checks JSON validity); no locking; no file mode; `read_recent` loads the whole file |
| D-12 | manifest.py | `capabilities` are hard-coded True (including `prime_agent` while Prime families default off); `tools` is the static 146-name roster while the host serves 108; version hard-coded; no digest; no gated-tool list |
| D-13 | oneclick.py | Exports `http://0.0.0.0:8000/sse` for a wildcard bind; launches even when preflight fails ("Continuing launch..."); token only via argv; SSE with no token runs open |
| D-14 | doctor.py | Port check hard-wired to 127.0.0.1; no policy, roster, token, template or audit-chain checks |
| D-15 | supervisor.py | `--stop` signals the child PID from the state file, so the supervisor restarts it; restart counter never resets; uptime measured from first start; giving up exits 0; no health probing; default command is the stdio server (exits at once, restart loop); non-atomic state writes; child shares the terminal process group |
| D-16 | sync.py | Compares the whole manifest including url/transport/auth, so any non-default export reports false drift; `--export-prompt` returns before the drift exit code; flags are reported but not compared; calls `generate_grokbot_manifest()` with no root |
| D-17 | emulator.py | Builds the registry without policy or approvals (not the production path); reads private `registry._tools`; default root is cwd |
| D-18 | tests | 22 tests, none drives a real transport; nothing runs an MCP client against the served app |
| D-19 | SETUP.md | Documents `--token "$MCP_AUTH_TOKEN"` (argv exposure) and `--host 0.0.0.0` with no auth guidance |
</defects>

<decisions>
## Decisions

- Reuse the MCP SDK (mcp 2.3.0): `mcp.server.transport_security.TransportSecuritySettings`
  (Host/Origin validation), `SseServerTransport(max_request_body_size=..., security_settings=...)`.
  Do not reimplement them.
- No new third-party dependencies. Python >= 3.11 (CI runs 3.12, 3.13, 3.14); portable stdlib only.
- Pure ASGI middleware only. Never `BaseHTTPMiddleware` (D-10).
- Fail closed: any security-relevant configuration problem raises before serving; a CLI maps it to exit 2.
- Tool calls run in a worker thread behind a `ToolGate` (one at a time by default). Before this, `registry.dispatch`
  ran on the event loop, so one slow tool froze `/healthz`, SSE keepalives and shutdown, `in_flight` could never be
  observed above zero, and tools that call `asyncio.run` (`mcp_session`, `telegram`, `discord`) failed with
  "asyncio.run() cannot be called from a running event loop". Interceptors run in the worker thread, so every
  interceptor and every structure it shares must be thread-safe. Serial by default because tools were written for
  the serial stdio host and share files and state without locks.
- Tool-call policy lives in interceptors (`interceptors.py`) so Phase 63 adds rate limit, breaker and
  metrics by composition, not by editing the handler again.
- The authenticated principal travels in `scope["state"]["principal"]`; MCP handlers read it from
  `ctx.request.state.principal` (`ServerRequestContext.request` is the Starlette `Request` on HTTP
  transports and `None` on stdio, where there is no principal and the caller is the local operator).
- Never write a token to any file, manifest, log or audit record. Audit stores argument key names and a
  SHA-256 digest of the canonical arguments by default, not values.
- Every new Python file starts with:
  `# SPDX-License-Identifier: AGPL-3.0-only` and `# Copyright (C) 2026 Spectrum Web Co`.
</decisions>

<contracts>
## Shared contracts (signatures are binding; add optional keyword arguments only)

Existing facts the units rely on:
- `omega_prime/mcp_server.py`: `SERVER_NAME`, `SERVER_VERSION = "6.0.0"`, `roster_names(text)`,
  `default_registry(root, home, *, policy, approval_log, env)`, `list_tools_handler(registry, roster)`,
  `call_tool_handler(registry, roster)`, `build_server(registry, roster)`, `main(argv)`.
- `omega_prime/tools/registry.py`: `ToolRegistry.schemas()`, `.dispatch(name, arguments) -> str`, and a
  method that reports whether a tool requires approval (find its exact name; it is the one returning
  `bool(tool is not None and tool.requires_approval)`).
- `omega_prime/policy/policy.py`: `SeatPolicy.load(path)` raises `FileNotFoundError`/`ValueError`.
- `omega_prime/tools/approvals.py`: `ApprovalLog.approve(tool, approved_by, *, bot_id=...)`, `.is_approved(tool)`.
- `omega_prime/grokbot/_io.py` (already written): `atomic_write_text`, `atomic_write_json`,
  `ensure_private_dir`, `read_secret_file`. Use it for every state/secret file.

### security.py (62-01)

```python
SCOPE_READ, SCOPE_CALL, SCOPE_ADMIN = "read", "call", "admin"      # admin implies call implies read
SCOPES = (SCOPE_READ, SCOPE_CALL, SCOPE_ADMIN)
MIN_TOKEN_LENGTH = 16
class SecurityConfigError(ValueError): ...

@dataclass(frozen=True)
class Principal:
    id: str                       # non-secret and stable, e.g. "env-token"
    scopes: frozenset[str]
    label: str = ""
    def allows(self, scope: str) -> bool: ...    # unknown scope -> False

def hash_token(token: str) -> str                  # sha256 hexdigest
def generate_token(prefix: str = "omk") -> str     # f"{prefix}_{secrets.token_urlsafe(32)}"
def parse_bearer(header: str | None) -> str | None # "Bearer <token>", scheme case-insensitive, one space, no inner whitespace

class TokenStore:
    def __init__(self, entries: Iterable[tuple[Principal, str]] = ()) -> None   # (principal, sha256 hex)
    @classmethod
    def from_token(cls, token: str, *, principal_id: str = "env-token",
                   scopes: Iterable[str] = (SCOPE_READ, SCOPE_CALL), label: str = "") -> TokenStore
        # raises SecurityConfigError when len(token) < MIN_TOKEN_LENGTH or a scope is unknown
    @property
    def enabled(self) -> bool                      # at least one entry
    def verify(self, presented: str | None) -> Principal | None
        # hash the presented value; hmac.compare_digest against EVERY entry; no early exit; None for None/empty
    def principals(self) -> list[Principal]

def is_loopback_host(host: str) -> bool            # 127.0.0.0/8, ::1, "localhost"; "", "0.0.0.0", "::" -> False
def check_bind_safety(host: str, *, auth_enabled: bool, allow_insecure: bool) -> None
    # raises SecurityConfigError("refusing to serve on <host> without authentication; ...") when
    # the host is not loopback, auth is disabled and allow_insecure is False

class AuthMiddleware:                              # pure ASGI 3
    def __init__(self, app, *, store: TokenStore, public_paths: Iterable[str] = ("/healthz", "/readyz"),
                 on_failure: Callable[[dict[str, Any]], None] | None = None) -> None
    # http: exact public path -> pass through. Else read ONLY the Authorization header; ignore ?token=.
    # Failure: 401, JSON {"error": "unauthorized", "detail": "..."}, headers
    #   WWW-Authenticate: Bearer realm="omega-prime", Cache-Control: no-store; call on_failure(
    #   {"reason": "missing"|"malformed"|"invalid", "path": str, "client": str | None}) - never the token.
    # Success: scope.setdefault("state", {})["principal"] = principal, then the app.
    # lifespan passes through; websocket is closed with code 1008.

def principal_from_scope(scope) -> Principal | None
def principal_from_request(request) -> Principal | None   # tolerates None and objects without .state
```

### interceptors.py (62-01)

```python
@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    principal: Principal | None            # None on stdio and on a no-auth loopback host
    transport: str = "stdio"               # "stdio" | "sse" | "http"
    request_id: str | None = None          # scope["state"].get("request_id") when a layer sets it

@dataclass(frozen=True)
class ToolDenial:
    code: str                              # "forbidden" | "rate_limited" | "circuit_open" | ...
    message: str
    retry_after: float | None = None

@dataclass(frozen=True)
class ToolOutcome:
    status: str                            # "ok" | "error" | "denied"
    is_error: bool
    duration_ms: float
    error: str | None = None
    denial_code: str | None = None

class ToolCallInterceptor(Protocol):
    def before(self, call: ToolCall) -> ToolDenial | None: ...
    def after(self, call: ToolCall, outcome: ToolOutcome) -> None: ...
# Semantics: interceptors run in order. The first denial stops the chain and the tool is NOT dispatched.
# `after` runs for every interceptor whose `before` ran (including the one that denied and those before
# it) so counters and in-flight bookkeeping stay balanced. An exception in `before` is a denial with
# code "interceptor_error" (fail closed). An exception in `after` is logged and swallowed.

def call_from_context(ctx, name, arguments, *, transport: str = "stdio") -> ToolCall
def run_tool_call(interceptors, call, dispatch) -> tuple[str, ToolOutcome]
    # dispatch: Callable[[], str]; returns the tool result payload (JSON text) and the outcome.
    # A denial yields the payload json.dumps({"error": f"{code}: {message}", "tool": name}).
class ScopeInterceptor:                    # denies code="forbidden" when a principal lacks SCOPE_CALL
class AuditInterceptor:                    # AuditInterceptor(tracer, *, args_mode="digest")
    # after(): tracer.log_event("tool_call", tool_name=name, caller=principal.id or "local",
    #   status=outcome.status, duration_ms=..., is_error=..., details={"arg_keys": sorted keys,
    #   "args_sha256": digest of canonical JSON of arguments, "transport": ..., "request_id": ...,
    #   "denial": code, "error": redacted first 200 chars}). args_mode "redacted" adds sanitize_payload(arguments).
class InFlightInterceptor:                 # .count property; before() +1, after() -1 (thread-safe)
```

### audit.py (62-02)

```python
class GrokBotAuditTracer:
    def __init__(self, log_path: Path | str | None = None, *, max_bytes: int = 10 * 1024 * 1024,
                 backups: int = 5) -> None
    log_path: Path
    def log_event(self, event: str, *, tool_name: str | None = None, caller: str = "grok-bot",
                  status: str = "ok", duration_ms: float = 0.0, is_error: bool = False,
                  details: dict[str, Any] | None = None) -> dict[str, Any]   # returns the stored record
    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]
    def verify_integrity(self, *, include_rotated: bool = False) -> tuple[bool, int, str]
def default_audit_path(root: Path | str) -> Path        # root/.planning/grokbot_audit.jsonl
def main(argv: list[str] | None = None) -> int          # verify [--path P] [--all] | tail [--path P] [-n N]
```
Record fields: `seq`, `timestamp`, `event`, `tool_name`, `caller`, `status`, `duration_ms`, `is_error`,
`details`, `prev`, `hash`. `hash = sha256(prev + canonical_json(record_without_hash))`, canonical JSON =
`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, genesis `prev = "0" * 64`.

### mcp_server.py library additions (62-01) and CLI (62-05)

```python
class RuntimeConfigError(ValueError): ...      # one-line message safe to print
@dataclass(frozen=True)
class Runtime:
    root: Path; home: Path; roster: list[str] | None; policy: SeatPolicy
    registry: ToolRegistry; approval_log: ApprovalLog
    tool_names: list[str]      # exactly what tools/list returns: registry order, filtered by roster
    gated_tools: list[str]     # subset of tool_names that require approval
def load_runtime(root, home=None, *, no_roster=False, approvals: Sequence[tuple[str, str]] = (),
                 env: Mapping[str, str] | None = None) -> Runtime
    # Fail closed: missing/invalid roster or policy, or a refused approval, raises RuntimeConfigError.
class ToolGate:                                  # added after 62-01 review; already in mcp_server.py
    def __init__(self, limit: int = 1) -> None   # ValueError when limit < 1
    async def run(self, fn, *args)               # fn(*args) in a worker thread, at most `limit` at a time;
                                                 # a cancelled caller keeps its slot until the thread ends
def call_tool_handler(registry, roster=None, *, interceptors=(), transport="stdio", gate: ToolGate | None = None)
def build_server(registry, roster=None, *, interceptors=(), transport="stdio", gate: ToolGate | None = None) -> Server
```
Tool calls run in a worker thread behind the gate (default: a private `ToolGate()`, one call at a time). Share ONE
gate between every server built on one registry.
CLI flags added by 62-05 to `python -m omega_prime.mcp_server` (remote ones apply to `--transport sse`):
`--public-url`, `--allow-host HOST[:PORT]` (repeat), `--allow-origin ORIGIN` (repeat), `--token-env NAME`
(default `MCP_AUTH_TOKEN`), `--token-file PATH`, `--token T` (deprecated: stderr warning), `--allow-insecure-no-auth`,
`--audit-log PATH` (env `OMEGA_PRIME_AUDIT_LOG`), `--max-body-bytes N` (default 1048576),
`--shutdown-grace SECONDS` (default 20). `--approve` works on both transports. Exit 2 on any configuration error.

### remote.py (62-05)

```python
def create_sse_app(root, *, token=None, token_store=None, home=None, no_roster=False, host="127.0.0.1",
                   port=8000, public_url=None, allowed_hosts=(), allowed_origins=(),
                   allow_insecure_no_auth=False, audit=None, approvals=(), max_body_bytes=1_048_576,
                   shutdown_grace=20.0, env=None, interceptors=()) -> Starlette
def serve_sse(root, host="127.0.0.1", port=8000, token=None, home=None, no_roster=False, **same_kwargs) -> int
create_mcp_sse_app = create_sse_app
```
`app.state` exposes `runtime`, `tool_names`, `audit`, `in_flight` (InFlightInterceptor), `shutting_down` (bool).
`/healthz` keeps `status`, `service`, `version` (= `SERVER_VERSION`), `rostered_tools` (= `len(tool_names)`) and adds
`package_version`, `auth` ("required" | "disabled"). `/readyz` keeps `ready` and adds `checks`; 503 when not ready.

### manifest.py (62-03)

`generate_manifest(root=None, *, host_url="http://127.0.0.1:8000/sse", transport="sse", auth_token=None,
public_url=None, home=None, env=None, token_env="MCP_AUTH_TOKEN", auth_enabled=None) -> dict`
keeps `manifest_version`, `bot`, `mcp_server`, `capabilities`; adds `mcp_server.approval_required`,
`mcp_server.endpoints` (`{"sse": url, "healthz": ...}` only for transport sse), `bot.integrity`
(`{"missing_skills": [], "missing_routines": []}`), top-level `digest` (sha256 of the canonical manifest
without `digest`). `auth_token` only decides `auth.type`; it is never stored.
`lint_template(root) -> TemplateLint(missing_skills, missing_routines, ok)`.
`served_tools(root, home=None, env=None) -> tuple[list[str], list[str]]` (served names, gated names) via
`load_runtime`.
</contracts>

<conventions>
## Conventions for every unit

- Edit only the files listed in the unit plan. Do not run tests, linters or formatters; the orchestrator
  verifies once per wave. Read the existing file and its tests first; keep every existing public name and
  every existing passing test valid unless the plan says to change it.
- Keep the code type-correct for `mypy` (`check_untyped_defs`) and `ruff` rules E4,E7,E9,F,I,UP,B,SIM,RUF,
  line length 88 (E501 ignored). No `print` of secrets. No new dependencies.
- Tests are hermetic: temp dirs, no network except 127.0.0.1 sockets, no sleeps over 2 seconds, injected
  clocks where timing matters.
</conventions>
