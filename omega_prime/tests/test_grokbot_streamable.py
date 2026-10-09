# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Streamable HTTP transport on a real 127.0.0.1 socket, driven by the MCP SDK.

A tiny Starlette app composes a stand-in auth middleware (`Bearer a` / `Bearer b`
become two principals), the `/mcp` route and a lifespan entering
`StreamableHttp.lifespan()`. Nothing leaves the loopback interface.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import subprocess
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx2
import pytest
import uvicorn
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server import Server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
from starlette.applications import Starlette
from starlette.types import ASGIApp, Receive, Scope, Send

from omega_prime.grokbot.security import Principal
from omega_prime.grokbot.streamable import StreamableHttp, build_streamable_http

ALICE = Principal("alice", frozenset({"read", "call"}))
BOB = Principal("bob", frozenset({"read", "call"}))
_PRINCIPALS = {b"Bearer a": ALICE, b"Bearer b": BOB}
_ACCEPT = "application/json, text/event-stream"
_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "1"},
    },
}


class _StandInAuth:
    """Map `Authorization: Bearer a|b` to a principal on `scope["state"]`."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            principal = _PRINCIPALS.get(headers.get(b"authorization", b""))
            if principal is not None:
                scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)


def _server() -> Server[Any]:
    async def list_tools(ctx: Any, params: Any) -> ListToolsResult:
        del ctx, params
        return ListToolsResult(
            tools=[
                Tool(
                    name="echo",
                    description="echo text",
                    input_schema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                )
            ]
        )

    async def call_tool(ctx: Any, params: Any) -> CallToolResult:
        del ctx
        text = str((params.arguments or {}).get("text", ""))
        return CallToolResult(content=[TextContent(type="text", text=text)])

    return Server("t", version="1", on_list_tools=list_tools, on_call_tool=call_tool)


class _Host:
    def __init__(self, server: uvicorn.Server, transport: StreamableHttp) -> None:
        self.transport = transport
        port = server.servers[0].sockets[0].getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        self.url = f"{self.base}/mcp"


@contextlib.contextmanager
def _serve(**options: Any) -> Iterator[_Host]:
    transport = build_streamable_http(_server(), **options)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        del app
        async with transport.lifespan():
            yield

    app = Starlette(routes=[transport.route], lifespan=lifespan)
    config = uvicorn.Config(
        _StandInAuth(app),
        host="127.0.0.1",
        port=0,
        log_level="warning",
        access_log=False,
        timeout_graceful_shutdown=2,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="streamable-test", daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("the test server did not start")
        time.sleep(0.02)
    try:
        yield _Host(server, transport)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _post(
    host: _Host,
    token: str | None,
    body: bytes | dict[str, Any],
    *,
    session: str | None = None,
) -> httpx2.Response:
    headers = {"Accept": _ACCEPT, "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if session is not None:
        headers["Mcp-Session-Id"] = session
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    with httpx2.Client(trust_env=False, timeout=10.0) as http:
        return http.post(host.url, content=content, headers=headers)


def _open_session(host: _Host, token: str = "a") -> str:
    response = _post(host, token, _INIT)
    assert response.status_code == 200
    return response.headers["mcp-session-id"]


def test_import_has_no_side_effects() -> None:
    code = (
        "import sys, threading; before = threading.active_count();"
        "import omega_prime.grokbot.streamable as m;"
        "assert threading.active_count() == before;"
        "assert hasattr(m, 'build_streamable_http')"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr


def test_route_is_raw_asgi_for_exact_mcp_path() -> None:
    transport = build_streamable_http(_server())
    assert transport.route.path == "/mcp"
    assert transport.route.methods == {"GET", "POST", "DELETE", "HEAD"}
    assert transport.manager.stateless is False


def test_client_initialize_list_and_call_as_principal_a() -> None:
    async def scenario(host: _Host) -> tuple[list[str], str]:
        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer a"}, trust_env=False
        ) as http:
            transport = streamable_http_client(host.url, http_client=http)
            async with Client(transport, mode="legacy", read_timeout_seconds=10.0) as c:
                listing = await c.list_tools()
                result = await c.call_tool("echo", {"text": "hello"})
        block = result.content[0]
        assert isinstance(block, TextContent)
        return [tool.name for tool in listing.tools], block.text

    with _serve() as host:
        names, text = asyncio.run(scenario(host))
    assert names == ["echo"]
    assert text == "hello"


def test_other_principal_gets_404_for_someone_elses_session() -> None:
    with _serve() as host:
        session = _open_session(host, "a")
        own = _post(
            host, "a", {"jsonrpc": "2.0", "id": 2, "method": "ping"}, session=session
        )
        stolen = _post(
            host, "b", {"jsonrpc": "2.0", "id": 2, "method": "ping"}, session=session
        )
        anonymous = _post(
            host, None, {"jsonrpc": "2.0", "id": 2, "method": "ping"}, session=session
        )
    assert own.status_code == 200
    assert stolen.status_code == 404
    assert anonymous.status_code == 404


def test_session_owner_is_principal_id_not_the_bearer_token() -> None:
    with _serve() as host:
        _open_session(host, "a")
        owners = host.transport.manager._session_owners
        assert [owner["client_id"] for owner in owners.values()] == ["alice"]
        assert "Bearer" not in repr(owners)


def test_body_over_limit_gets_413() -> None:
    with _serve(max_body_bytes=256) as host:
        big = b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":"' + (b"x" * 1024)
        response = _post(host, "a", big + b'"}}')
        small = _post(host, "a", _INIT)
    assert response.status_code == 413
    assert small.status_code == 200


def test_more_than_max_sessions_gets_503() -> None:
    with _serve(max_sessions=2) as host:
        first = _open_session(host, "a")
        _open_session(host, "b")
        refused = _post(host, "a", _INIT)
        deleted = _delete(host, "a", first)
        admitted = _post(host, "a", _INIT)
    assert refused.status_code == 503
    assert deleted.status_code == 200
    assert admitted.status_code == 200


def _delete(host: _Host, token: str, session: str) -> httpx2.Response:
    with httpx2.Client(trust_env=False, timeout=10.0) as http:
        return http.delete(
            host.url,
            headers={"Authorization": f"Bearer {token}", "Mcp-Session-Id": session},
        )


def test_delete_ends_the_session() -> None:
    with _serve() as host:
        session = _open_session(host, "a")
        denied = _delete(host, "b", session)
        deleted = _delete(host, "a", session)
        after = _post(
            host,
            "a",
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            session=session,
        )
    assert denied.status_code == 404
    assert deleted.status_code == 200
    assert after.status_code == 404


def test_get_without_session_id_is_a_4xx_not_a_hang() -> None:
    with _serve() as host, httpx2.Client(trust_env=False, timeout=5.0) as http:
        response = http.get(
            host.url, headers={"Authorization": "Bearer a", "Accept": _ACCEPT}
        )
    assert 400 <= response.status_code < 500


@pytest.mark.parametrize("method", ["PUT", "PATCH", "OPTIONS"])
def test_other_methods_get_405(method: str) -> None:
    with _serve() as host, httpx2.Client(trust_env=False, timeout=5.0) as http:
        response = http.request(method, host.url, headers={"Authorization": "Bearer a"})
    assert response.status_code == 405


def test_mcp_path_does_not_redirect() -> None:
    with (
        _serve() as host,
        httpx2.Client(trust_env=False, timeout=5.0, follow_redirects=False) as http,
    ):
        response = http.post(
            host.url,
            content=json.dumps(_INIT),
            headers={
                "Authorization": "Bearer a",
                "Accept": _ACCEPT,
                "Content-Type": "application/json",
            },
        )
    assert response.status_code == 200
