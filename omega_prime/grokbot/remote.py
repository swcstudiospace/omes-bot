"""Remote MCP Server Transport over SSE and HTTP.

Enables cloud-hosted Grok Bots and remote clients to connect to Omega Prime
tool host securely with bearer token auth, CORS, and health probes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from omega_prime.mcp_server import build_server, default_registry, roster_names
from omega_prime.policy.policy import SeatPolicy
from omega_prime.tools.approvals import ApprovalLog


def create_sse_app(
    root: Path,
    *,
    token: str | None = None,
    home: Path | None = None,
    no_roster: bool = False,
) -> Starlette:
    """Create a Starlette ASGI app hosting the MCP server over SSE."""
    home = home or Path.home()
    roster = None
    if not no_roster:
        roster_path = (
            root / "omega_prime" / "contracts" / "tool-rosters" / "omega-prime.yaml"
        )
        if roster_path.is_file():
            roster = roster_names(roster_path.read_text(encoding="utf-8"))

    policy = None
    policy_path = root / "omega_prime" / "contracts" / "policies" / "omega-prime.json"
    if policy_path.is_file():
        try:
            policy = SeatPolicy.load(policy_path)
        except Exception:
            policy = None

    log = ApprovalLog()
    registry = default_registry(
        root, home, policy=policy, approval_log=log, env=dict(os.environ)
    )
    server = build_server(registry, roster)
    sse_transport = SseServerTransport("/messages/")

    async def auth_middleware(request: Request, call_next: Any) -> Response:
        if token and (
            request.url.path == "/sse" or request.url.path.startswith("/messages")
        ):
            auth_header = request.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            if auth_header != expected and request.query_params.get("token") != token:
                return JSONResponse(
                    {"error": "Unauthorized: invalid bearer token"}, status_code=401
                )
        return await call_next(request)

    async def healthz(request: Request) -> JSONResponse:
        del request
        tool_count = len(roster) if roster is not None else 108
        return JSONResponse(
            {
                "status": "healthy",
                "service": "omega-prime-mcp-server",
                "version": "6.0.0",
                "rostered_tools": tool_count,
            }
        )

    async def readyz(request: Request) -> JSONResponse:
        del request
        return JSONResponse(
            {
                "ready": True,
                "registry": "loaded",
                "policy": "active" if policy is not None else "default",
            }
        )

    async def handle_sse(request: Request) -> Response:
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
        return Response()

    routes = [
        Route("/healthz", healthz, methods=["GET"]),
        Route("/readyz", readyz, methods=["GET"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        ),
    ]
    if token:
        middleware.append(Middleware(BaseHTTPMiddleware, dispatch=auth_middleware))

    app = Starlette(routes=routes, middleware=middleware)

    # Wrap with auth middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def serve_sse(
    root: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    token: str | None = None,
    home: Path | None = None,
    no_roster: bool = False,
) -> int:
    """Run uvicorn server serving the MCP SSE transport."""
    app = create_sse_app(root, token=token, home=home, no_roster=no_roster)
    print(f"Serving Omega Prime MCP on http://{host}:{port}/sse")
    print(f"Healthcheck: http://{host}:{port}/healthz")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


create_mcp_sse_app = create_sse_app
