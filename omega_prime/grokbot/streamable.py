# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""MCP Streamable HTTP at `/mcp`, bounded and bound to the calling principal.

`build_streamable_http` wraps the SDK's `StreamableHTTPSessionManager` in
stateful mode and exposes a Starlette `Route` for `/mcp` plus the manager's
lifespan, so the host (`remote.create_sse_app`) can mount the route next to
legacy SSE and enter `lifespan()` once in its own Starlette lifespan.

The SDK enforces the bounds: a body over `max_body_bytes` answers 413, a request
that would open session number `max_sessions + 1` answers 503, and a session with
no request in flight for `session_idle_timeout` seconds is dropped (its id then
answers 404).

A session belongs to the principal that opened it. The SDK keeps a per-session
owner taken from `scope["user"]`; before delegating, the endpoint copies the
principal `AuthMiddleware` attached to the scope into an `AuthenticatedUser`
whose `client_id` is the (non-secret) principal id. A different principal
presenting someone else's `Mcp-Session-Id` is answered exactly like an unknown
session (404). The placeholder `AccessToken.token` is never the bearer token.
With no principal (authentication disabled) `scope["user"]` is left alone and
sessions are unowned.

Importing this module has no side effects: nothing is constructed or started
until `build_streamable_http` is called, and the manager only runs once its
`lifespan()` is entered (twice is an SDK error). A request arriving before that
gets the SDK's own error.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any

from mcp.server import Server
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from omega_prime.grokbot.security import principal_from_scope

__all__ = ["StreamableHttp", "build_streamable_http"]

MCP_PATH = "/mcp"


@dataclass
class StreamableHttp:
    """The manager, its `/mcp` route and the lifespan the host must enter once."""

    manager: StreamableHTTPSessionManager
    route: Route

    def lifespan(self) -> AbstractAsyncContextManager[None]:
        """`async with` this once in the host's Starlette lifespan."""
        return self.manager.run()


class _PrincipalBoundEndpoint:
    """Raw ASGI endpoint: copy our principal into the SDK's session owner."""

    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        self._manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        principal = principal_from_scope(scope)
        if principal is not None:
            scope["user"] = AuthenticatedUser(
                AccessToken(
                    token=f"principal:{principal.id}",
                    client_id=principal.id,
                    scopes=sorted(principal.scopes),
                )
            )
        await self._manager.handle_request(scope, receive, send)


def build_streamable_http(
    server: Server[Any],
    *,
    security_settings: TransportSecuritySettings | None = None,
    max_body_bytes: int = 1_048_576,
    max_sessions: int = 64,
    session_idle_timeout: float = 1800.0,
    json_response: bool = False,
) -> StreamableHttp:
    """Serve `server` over Streamable HTTP with stateful, principal-bound sessions."""
    manager = StreamableHTTPSessionManager(
        app=server,
        stateless=False,
        security_settings=security_settings,
        max_request_body_size=max_body_bytes,
        max_sessions=max_sessions,
        session_idle_timeout=session_idle_timeout,
        json_response=json_response,
    )
    route = Route(
        MCP_PATH,
        _PrincipalBoundEndpoint(manager),
        methods=["GET", "POST", "DELETE"],
    )
    return StreamableHttp(manager=manager, route=route)
