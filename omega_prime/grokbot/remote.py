# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Remote MCP tool host over SSE for Grok Bots and other MCP clients.

`create_sse_app` composes the pieces into one ASGI app and fails closed: it raises
before serving when authentication is missing on a non-loopback bind, when the
roster or seat policy is invalid, or when the transport settings are malformed.

- Authentication: pure-ASGI bearer `AuthMiddleware` over a hashed `TokenStore`.
  `/healthz` and `/readyz` are public; nothing else is.
- Transport security: the MCP SDK's `TransportSecuritySettings` (Host and Origin
  validation) and its request-body limit; CORS is added only for origins named
  explicitly and never answers `*`.
- Tool calls: interceptors count in-flight calls, enforce the `call` scope and
  write one hash-chained `tool_call` audit record; calls run in a worker thread
  behind one `ToolGate`, so a slow tool never freezes health, keepalives or
  shutdown. Failed authentication writes an `auth_failure` record (never the token).
- Lifecycle: `serve_sse` returns 2 on configuration errors and drains gracefully:
  the first SIGTERM/SIGINT flips `/readyz` to 503 and waits for in-flight tool
  calls (bounded by `shutdown_grace`), a second signal forces exit.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import time
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from omega_prime import __version__ as PACKAGE_VERSION
from omega_prime.grokbot.audit import GrokBotAuditTracer, default_audit_path
from omega_prime.grokbot.interceptors import (
    AuditInterceptor,
    InFlightInterceptor,
    ScopeInterceptor,
    ToolCallInterceptor,
)
from omega_prime.grokbot.security import (
    AuthMiddleware,
    SecurityConfigError,
    TokenStore,
    check_bind_safety,
    is_loopback_host,
)
from omega_prime.mcp_server import (
    SERVER_NAME,
    SERVER_VERSION,
    Runtime,
    ToolGate,
    build_server,
    load_runtime,
)

# uvicorn's logger is the one that is configured when this runs under `serve_sse`.
logger = logging.getLogger("uvicorn.error")

PUBLIC_PATHS = ("/healthz", "/readyz")
DEFAULT_MAX_BODY_BYTES = 1_048_576
_LOOPBACK_HOST_PATTERNS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
_WILDCARD_BINDS = frozenset({"", "0.0.0.0", "::", "[::]"})
_CORS_METHODS = ["GET", "POST", "OPTIONS", "DELETE"]
_CORS_HEADERS = ["Authorization", "Content-Type", "Mcp-Session-Id", "Last-Event-ID"]
_AUDITED_PATH_CHARS = 200
_GUARDED_PREFIXES = ("/sse", "/messages")


def _bracket(host: str) -> str:
    """`host` as it appears in a Host header (IPv6 literals in brackets)."""
    name = host.strip()
    if name.startswith("[") and name.endswith("]"):
        return name
    return f"[{name}]" if ":" in name else name


def _parse_public_url(public_url: str) -> tuple[str, str, str]:
    """(origin, hostname, netloc) of a public URL; any path is ignored."""
    parsed = urlsplit(public_url.strip())
    try:
        port = parsed.port
    except ValueError:
        port = -1
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port == -1
    ):
        raise SecurityConfigError(
            "public URL must be an http(s) URL with a host, an optional port "
            "and no credentials"
        )
    return f"{parsed.scheme}://{parsed.netloc}", parsed.hostname, parsed.netloc


def _clean_entries(values: Iterable[str], what: str) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item:
            raise SecurityConfigError(f"empty {what} entry")
        if "*" in item and not item.endswith(":*"):
            raise SecurityConfigError(
                f"{what} {item!r} is not supported; wildcards are only allowed as a "
                "trailing :* port pattern"
            )
        if item == ":*":
            raise SecurityConfigError(f"{what} {item!r} names no host")
        cleaned.append(item)
    return cleaned


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _origin_allowed(origin: str, allowed: Sequence[str]) -> bool:
    """Same matching rule as the SDK: exact, or `base:*` for any port."""
    for entry in allowed:
        if origin == entry:
            return True
        if entry.endswith(":*") and origin.startswith(entry[:-2] + ":"):
            return True
    return False


class _OriginGuard:
    """Pure-ASGI Origin validation for `/sse` and `/messages`.

    Used when the SDK's Host validation is off (a non-loopback bind with bearer
    auth and no configured public host), because the SDK switches Host and Origin
    checks together. A request without an Origin header (not a browser) passes.
    """

    def __init__(self, app: Any, *, allowed_origins: Sequence[str]) -> None:
        self.app = app
        self.allowed_origins = tuple(allowed_origins)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith(
            _GUARDED_PREFIXES
        ):
            origin: str | None = None
            for key, value in scope.get("headers", ()):
                if key.lower() == b"origin":
                    origin = value.decode("latin-1")
                    break
            if origin and not _origin_allowed(origin, self.allowed_origins):
                response = PlainTextResponse("Invalid Origin header", status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class _SseEndpoint:
    """ASGI endpoint for `GET /sse`: one MCP session per connection.

    A rejected request (Host/Origin validation) has already been answered by the
    transport, so nothing more is sent. Being a raw ASGI app, it never emits a
    second response after the stream ends.
    """

    def __init__(self, transport: SseServerTransport, server: Server) -> None:
        self._transport = transport
        self._server = server

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        async with contextlib.AsyncExitStack() as stack:
            try:
                streams = await stack.enter_async_context(
                    self._transport.connect_sse(scope, receive, send)
                )
            except ValueError:
                return
            await self._server.run(
                streams[0], streams[1], self._server.create_initialization_options()
            )


def _audit_writable(path: Path) -> bool:
    """Whether the audit file (or the directory that will hold it) accepts writes."""
    if path.exists():
        return path.is_file() and os.access(path, os.W_OK)
    directory = path.parent
    while not directory.exists() and directory != directory.parent:
        directory = directory.parent
    return directory.is_dir() and os.access(directory, os.W_OK | os.X_OK)


def create_sse_app(
    root: Path | str,
    *,
    token: str | None = None,
    token_store: TokenStore | None = None,
    home: Path | None = None,
    no_roster: bool = False,
    host: str = "127.0.0.1",
    port: int = 8000,
    public_url: str | None = None,
    allowed_hosts: Sequence[str] = (),
    allowed_origins: Sequence[str] = (),
    allow_insecure_no_auth: bool = False,
    audit: GrokBotAuditTracer | None = None,
    approvals: Sequence[tuple[str, str]] = (),
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    shutdown_grace: float = 20.0,
    env: dict[str, str] | None = None,
    interceptors: Sequence[ToolCallInterceptor] = (),
) -> Starlette:
    """Build the Starlette app hosting the MCP server over SSE.

    Raises `SecurityConfigError` (no authentication on a non-loopback bind, a
    short token, a malformed public URL or host/origin entry),
    `RuntimeConfigError` (invalid roster, seat policy or approval) or
    `ValueError` (invalid limit) before anything is served. `host` and `port` are
    the address the caller will bind; they only shape Host validation and the
    bind-safety check. `token` is the single bearer token of an `env-token`
    principal; `token_store` replaces it.
    """
    root = Path(root)
    if shutdown_grace < 0:
        raise ValueError("shutdown_grace must not be negative")
    if max_body_bytes <= 0:
        raise ValueError("max_body_bytes must be a positive number of bytes")

    if token_store is not None:
        store = token_store
    elif token:
        store = TokenStore.from_token(token)
    else:
        store = TokenStore()
    check_bind_safety(
        host, auth_enabled=store.enabled, allow_insecure=allow_insecure_no_auth
    )

    extra_hosts = _clean_entries(allowed_hosts, "allowed host")
    origins = _clean_entries(allowed_origins, "allowed origin")

    host_patterns: list[str] = list(_LOOPBACK_HOST_PATTERNS)
    if host.strip() not in _WILDCARD_BINDS:
        host_patterns.append(f"{_bracket(host)}:{port}")
    if public_url:
        origin, hostname, netloc = _parse_public_url(public_url)
        name = _bracket(hostname)
        host_patterns += [name, f"{name}:*", netloc]
        origins.append(origin)
    host_patterns += extra_hosts
    host_patterns = _unique(host_patterns)
    origins = _unique(origins)

    runtime: Runtime = load_runtime(
        root, home, no_roster=no_roster, approvals=approvals, env=env
    )
    tracer = (
        audit if audit is not None else GrokBotAuditTracer(default_audit_path(root))
    )
    in_flight = InFlightInterceptor()
    # Order matters: a denial stops the chain, and `after` only runs for
    # interceptors whose `before` ran. Observers (audit, later metrics) must
    # therefore come BEFORE denying interceptors (scope, later rate limits), or a
    # denied call would leave no record. In-flight accounting stays first.
    chain: tuple[ToolCallInterceptor, ...] = (
        in_flight,
        AuditInterceptor(tracer),
        ScopeInterceptor(),
        *interceptors,
    )
    gate = ToolGate()

    host_validation = is_loopback_host(host) or bool(public_url) or bool(extra_hosts)
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=host_validation,
        allowed_hosts=host_patterns,
        allowed_origins=origins,
    )
    sse_transport = SseServerTransport(
        "/messages/", security_settings=security, max_request_body_size=max_body_bytes
    )
    server = build_server(
        runtime.registry,
        runtime.roster,
        interceptors=chain,
        transport="sse",
        gate=gate,
    )

    auth_mode = "required" if store.enabled else "disabled"

    async def healthz(request: Request) -> JSONResponse:
        del request
        return JSONResponse(
            {
                "status": "healthy",
                "service": "omega-prime-mcp-server",
                "version": SERVER_VERSION,
                "package_version": PACKAGE_VERSION,
                "rostered_tools": len(runtime.tool_names),
                "auth": auth_mode,
            }
        )

    async def readyz(request: Request) -> JSONResponse:
        shutting_down = bool(request.app.state.shutting_down)
        checks = {
            "registry": "ok" if runtime.tool_names else "fail",
            "roster": "ok" if runtime.roster is not None else "disabled",
            "policy": "ok",
            "audit": "ok" if _audit_writable(tracer.log_path) else "fail",
            "shutdown": "draining" if shutting_down else "ok",
        }
        ready = (
            checks["registry"] == "ok" and checks["audit"] == "ok" and not shutting_down
        )
        return JSONResponse(
            {"ready": ready, "checks": checks}, status_code=200 if ready else 503
        )

    def record_auth_failure(event: dict[str, Any]) -> None:
        tracer.log_event(
            "auth_failure",
            caller="anonymous",
            status="denied",
            is_error=True,
            details={
                "reason": event.get("reason"),
                "path": str(event.get("path", ""))[:_AUDITED_PATH_CHARS],
                "client": event.get("client"),
            },
        )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        del app
        logger.info(
            "Omega Prime MCP host ready: %d tools, auth %s, audit %s",
            len(runtime.tool_names),
            auth_mode,
            tracer.log_path,
        )
        if not host_validation:
            logger.info(
                "Host header validation is off (bearer auth is the control); "
                "set a public URL or allowed hosts to enable it"
            )
        try:
            yield
        finally:
            tracer.close()

    middleware: list[Middleware] = []
    if origins:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=list(origins),
                allow_methods=_CORS_METHODS,
                allow_headers=_CORS_HEADERS,
                allow_credentials=False,
            )
        )
    if store.enabled:
        middleware.append(
            Middleware(
                AuthMiddleware,
                store=store,
                public_paths=PUBLIC_PATHS,
                on_failure=record_auth_failure,
            )
        )
    if not host_validation:
        middleware.append(Middleware(_OriginGuard, allowed_origins=origins))

    routes = [
        Route("/healthz", healthz, methods=["GET"]),
        Route("/readyz", readyz, methods=["GET"]),
        Route("/sse", _SseEndpoint(sse_transport, server), methods=["GET"]),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]
    app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
    app.state.runtime = runtime
    app.state.tool_names = list(runtime.tool_names)
    app.state.audit = tracer
    app.state.in_flight = in_flight
    app.state.gate = gate
    app.state.shutting_down = False
    return app


class GracefulServer(uvicorn.Server):
    """A uvicorn server that drains in-flight tool calls before exiting.

    The first shutdown request sets `state.shutting_down` (so `/readyz` answers
    503 and a load balancer stops routing here) and starts a `grace`-second
    countdown; the server exits once `state.in_flight.count` reaches zero or the
    countdown ends. A second request forces exit. Unlike uvicorn's default, the
    first signal does not stop SSE streams at once, so results of running calls
    can still be delivered, and the process is not re-signalled after a clean
    drain (`serve_sse` returns normally).
    """

    def __init__(
        self,
        config: uvicorn.Config,
        *,
        state: Any,
        grace: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(config)
        self._state = state
        self._grace = grace
        self._clock = clock
        self._deadline: float | None = None

    @property
    def draining(self) -> bool:
        return self._deadline is not None

    def request_shutdown(self) -> None:
        """First call begins the drain; any later call forces exit."""
        if self._deadline is not None:
            self.force_exit = True
            self.should_exit = True
            return
        self._state.shutting_down = True
        self._deadline = self._clock() + self._grace

    def drain_complete(self) -> bool:
        """True once a drain began and no call is in flight or the grace elapsed."""
        if self._deadline is None:
            return False
        return self._state.in_flight.count == 0 or self._clock() >= self._deadline

    def handle_exit(self, sig: int, frame: Any) -> None:
        del sig, frame
        self.request_shutdown()

    async def on_tick(self, counter: int) -> bool:
        if not self.should_exit and self.drain_complete():
            self.should_exit = True
        return await super().on_tick(counter)


ACCESS_LOGGER_NAME = "uvicorn.access"
_ACCESS_ARGS_LENGTH = 5  # (client_addr, method, full_path, http_version, status)


class StripQueryFromAccessLog(logging.Filter):
    """Drop the query string from uvicorn's access-log request line.

    uvicorn logs `'%s - "%s %s HTTP/%s" %d'` with the full path including `?...`.
    A client that sends a credential in the query string (`/sse?token=...`, which
    this host refuses) would still leak it into the server log, and
    `/messages/?session_id=...` would log the session id. The filter rewrites the
    path argument to the part before the first `?`. Records of any other shape are
    left untouched and the filter never raises or drops a record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            args = record.args
            if (
                isinstance(args, tuple)
                and len(args) == _ACCESS_ARGS_LENGTH
                and isinstance(args[2], str)
                and "?" in args[2]
            ):
                record.args = (*args[:2], args[2].partition("?")[0], *args[3:])
        except Exception:
            return True
        return True


def install_access_log_filter() -> StripQueryFromAccessLog:
    """Attach `StripQueryFromAccessLog` to `uvicorn.access` once; return it.

    Idempotent: a filter already on the logger is reused, so repeated calls (for
    example several `serve_sse` runs in one process) never stack filters.
    """
    access_logger = logging.getLogger(ACCESS_LOGGER_NAME)
    for existing in access_logger.filters:
        if isinstance(existing, StripQueryFromAccessLog):
            return existing
    installed = StripQueryFromAccessLog()
    access_logger.addFilter(installed)
    return installed


def serve_sse(
    root: Path | str,
    host: str = "127.0.0.1",
    port: int = 8000,
    token: str | None = None,
    home: Path | None = None,
    no_roster: bool = False,
    *,
    token_store: TokenStore | None = None,
    public_url: str | None = None,
    allowed_hosts: Sequence[str] = (),
    allowed_origins: Sequence[str] = (),
    allow_insecure_no_auth: bool = False,
    audit: GrokBotAuditTracer | None = None,
    approvals: Sequence[tuple[str, str]] = (),
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    shutdown_grace: float = 20.0,
    env: dict[str, str] | None = None,
    interceptors: Sequence[ToolCallInterceptor] = (),
) -> int:
    """Serve the MCP SSE host until a shutdown signal; 0 after a clean exit.

    Returns 2 after printing `omega-prime-mcp-server: <reason>` to stderr when
    the configuration is refused (see `create_sse_app`).
    """
    try:
        if not 0 <= port <= 65535:
            raise ValueError(f"port {port} is out of range")
        app = create_sse_app(
            root,
            token=token,
            token_store=token_store,
            home=home,
            no_roster=no_roster,
            host=host,
            port=port,
            public_url=public_url,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
            allow_insecure_no_auth=allow_insecure_no_auth,
            audit=audit,
            approvals=approvals,
            max_body_bytes=max_body_bytes,
            shutdown_grace=shutdown_grace,
            env=env,
            interceptors=interceptors,
        )
    except ValueError as exc:
        print(f"omega-prime-mcp-server: {exc}", file=sys.stderr)
        return 2
    runtime: Runtime = app.state.runtime
    store_enabled = token_store.enabled if token_store is not None else bool(token)
    auth = "required" if store_enabled else "off"
    print(
        f"Serving {SERVER_NAME} MCP on http://{host}:{port}/sse "
        f"({len(runtime.tool_names)} tools, authentication {auth})"
    )
    print(f"Healthcheck: http://{host}:{port}/healthz")
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        timeout_graceful_shutdown=max(1, int(shutdown_grace)),
    )
    # After `Config` (which applies uvicorn's logging configuration), before serving.
    install_access_log_filter()
    server = GracefulServer(config, state=app.state, grace=shutdown_grace)
    try:
        server.run()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0


create_mcp_sse_app = create_sse_app

__all__ = [
    "ACCESS_LOGGER_NAME",
    "DEFAULT_MAX_BODY_BYTES",
    "PUBLIC_PATHS",
    "GracefulServer",
    "StripQueryFromAccessLog",
    "create_mcp_sse_app",
    "create_sse_app",
    "install_access_log_filter",
    "serve_sse",
]
