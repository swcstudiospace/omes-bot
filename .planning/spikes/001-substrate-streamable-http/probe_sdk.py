#!/usr/bin/env python3
"""Spike 001 (b): official MCP Python SDK (mcp>=2) Streamable HTTP client vs substrate-mcp.

Runs with the repo's .venv python (mcp 2.3.x, httpx2). For each case it opens
``mcp.Client(streamable_http_client(url, http_client=...))``, records the negotiated
protocol version, lists tools and calls harmless read-only tools, and records whether
``CallToolResult.is_error`` surfaces. An httpx2 event hook logs every HTTP exchange
(method, MCP headers, JSON-RPC method, status, content-type, error bodies) so the
negotiation sequence (server/discover probe -> initialize fallback) is visible.

Only read-only tools are called: memory_brief, graph_get, plus a deliberately invalid
graph_get and an unknown tool name to provoke isError. Tokens come from the env var
named by --token-env (never printed) and are redacted from all output.

    ../../../.venv/bin/python probe_sdk.py
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import os
import socket
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import anyio
import httpx2
from mcp import Client, MCPError
from mcp.client.streamable_http import streamable_http_client
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, MODERN_PROTOCOL_VERSIONS

HERE = Path(__file__).resolve().parent
DUMMY_GRAPH = "ut-spike001-00000000"
BODY_LIMIT = 2000
CASE_DEADLINE_S = 45

_TOKEN = ""

READ_ONLY_CALLS = [
    ("memory_brief", {"repo": "spike/omega-001"}),
    ("graph_get", {"graph_id": DUMMY_GRAPH}),
    ("graph_get", {}),  # missing required arg -> server returns isError
    ("no_such_tool", {}),  # unknown tool -> server returns isError
]


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(_TOKEN, "[REDACTED]") if _TOKEN else value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def describe_exc(exc: BaseException) -> dict:
    out: dict[str, Any] = {"exception": f"{type(exc).__module__}.{type(exc).__name__}", "message": str(exc)}
    if isinstance(exc, MCPError):
        out["mcp_error"] = {"code": exc.code, "message": exc.message, "data": exc.data}
    if isinstance(exc, BaseExceptionGroup):
        out["group"] = [describe_exc(e) for e in exc.exceptions]
    if exc.__cause__ is not None:
        out["cause"] = describe_exc(exc.__cause__)
    out["traceback_tail"] = traceback.format_exception(exc)[-3:]
    return out


def make_hooks(wire: list[dict]):
    async def on_request(request: httpx2.Request) -> None:
        entry: dict[str, Any] = {"t": round(time.monotonic(), 3), "dir": "request", "method": request.method, "url": str(request.url)}
        for name in ("accept", "content-type", "mcp-protocol-version", "mcp-session-id", "mcp-method", "mcp-name", "authorization"):
            value = request.headers.get(name)
            if value is not None:
                entry[name] = "Bearer [REDACTED]" if name == "authorization" else value
        try:
            body = json.loads(request.content or b"null")
            if isinstance(body, dict):
                entry["jsonrpc_method"] = body.get("method")
                entry["jsonrpc_id"] = body.get("id")
                if body.get("method") in ("initialize", "server/discover"):
                    entry["params"] = body.get("params")
        except Exception:  # noqa: BLE001 - streaming or non-JSON body
            pass
        wire.append(entry)

    async def on_response(response: httpx2.Response) -> None:
        entry: dict[str, Any] = {
            "t": round(time.monotonic(), 3),
            "dir": "response",
            "method": response.request.method,
            "status": response.status_code,
            "content-type": response.headers.get("content-type"),
            "mcp-session-id": response.headers.get("mcp-session-id"),
        }
        if response.status_code >= 400:
            try:
                await response.aread()
                entry["body"] = response.text[:BODY_LIMIT]
            except Exception as exc:  # noqa: BLE001
                entry["body_error"] = repr(exc)
        wire.append(entry)

    return {"request": [on_request], "response": [on_response]}


def tool_result(result: Any) -> dict:
    texts = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        texts.append(text[:BODY_LIMIT] if isinstance(text, str) else repr(block)[:200])
    return {"is_error": result.is_error, "content_text": texts, "structured_content": result.structured_content}


async def run_case(name: str, url: str, mode: str, headers: dict, calls: list) -> dict:
    wire: list[dict] = []
    rec: dict[str, Any] = {"case": name, "url": url, "mode": mode, "extra_headers": {k: ("Bearer [REDACTED]" if k.lower() == "authorization" else v) for k, v in headers.items()}}
    stage = "connect"
    start = time.monotonic()
    try:
        with anyio.fail_after(CASE_DEADLINE_S):
            async with httpx2.AsyncClient(
                headers=headers,
                timeout=httpx2.Timeout(15.0, read=30.0),
                event_hooks=make_hooks(wire),
            ) as http_client:
                transport = streamable_http_client(url, http_client=http_client)
                async with Client(transport, mode=mode, cache=None, read_timeout_seconds=20) as client:
                    rec["connected"] = True
                    rec["protocol_version"] = client.protocol_version
                    info = client.server_info
                    rec["server_info"] = info.model_dump(mode="json", exclude_none=True) if info else None
                    caps = client.server_capabilities
                    rec["server_capabilities"] = caps.model_dump(mode="json", exclude_none=True) if caps else None
                    stage = "list_tools"
                    try:
                        listed = await client.list_tools()
                        rec["tools"] = [t.name for t in listed.tools]
                    except Exception as exc:  # noqa: BLE001
                        rec["list_tools_error"] = describe_exc(exc)
                    rec["calls"] = []
                    for tool, arguments in calls:
                        stage = f"call_tool {tool}"
                        call: dict[str, Any] = {"tool": tool, "arguments": arguments}
                        t0 = time.monotonic()
                        try:
                            call["result"] = tool_result(await client.call_tool(tool, arguments))
                        except Exception as exc:  # noqa: BLE001
                            call["error"] = describe_exc(exc)
                        call["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 1)
                        rec["calls"].append(call)
                    stage = "close"
    except Exception as exc:  # noqa: BLE001 - includes ExceptionGroup and TimeoutError
        rec.setdefault("connected", False)
        rec["failed_at"] = stage
        rec["error"] = describe_exc(exc)
    rec["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    rec["wire"] = wire
    return rec


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def run_all(base: str, token: str) -> list[dict]:
    mcp_url = base + "/mcp"
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    modern = MODERN_PROTOCOL_VERSIONS[-1]
    cases = [
        ("S01 mode=auto (SDK default)", mcp_url, "auto", auth, READ_ONLY_CALLS),
        ("S02 mode=legacy (initialize handshake only)", mcp_url, "legacy", auth, READ_ONLY_CALLS),
        (f"S03 mode={modern} pinned (no handshake)", mcp_url, modern, auth, READ_ONLY_CALLS[:2]),
        ("S04 mode=auto, bogus bearer token", mcp_url, "auto", {"Authorization": "Bearer spike-001-bogus-token"}, READ_ONLY_CALLS[1:2]),
        ("S05 mode=auto, no Authorization header", mcp_url, "auto", {}, READ_ONLY_CALLS[1:2]),
        ("S06 mode=auto, wrong path (/mcp/ trailing slash)", mcp_url + "/", "auto", auth, READ_ONLY_CALLS[1:2]),
        ("S07 mode=auto, wrong path (/)", base + "/", "auto", auth, READ_ONLY_CALLS[1:2]),
        ("S08 mode=auto, substrate down (closed port)", f"http://127.0.0.1:{free_port()}/mcp", "auto", auth, READ_ONLY_CALLS[1:2]),
    ]
    return [await run_case(*case) for case in cases]


def summarize(cases: list[dict]) -> list[str]:
    lines = []
    for rec in cases:
        if rec.get("connected"):
            head = f"connected protocol={rec.get('protocol_version')} tools={len(rec.get('tools') or [])}"
            calls = []
            for call in rec.get("calls", []):
                if "result" in call:
                    calls.append(f"{call['tool']}:isError={call['result']['is_error']}")
                else:
                    calls.append(f"{call['tool']}:raised {call['error']['exception'].rsplit('.', 1)[-1]}")
            head += " | " + ", ".join(calls)
            if "list_tools_error" in rec:
                head += f" | list_tools raised {rec['list_tools_error']['message'][:120]}"
        else:
            err = rec.get("error", {})
            head = f"FAILED at {rec.get('failed_at')}: {err.get('exception', '').rsplit('.', 1)[-1]}: {err.get('message', '')[:160]}"
        statuses = [f"{w['method']} {w['status']}" for w in rec["wire"] if w["dir"] == "response"]
        lines.append(f"{rec['case']}\n    {head}\n    wire: {statuses}")
    return lines


def main() -> int:
    global _TOKEN
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:7410")
    parser.add_argument("--token-env", default=None, help="env var holding a bearer token (never printed)")
    parser.add_argument("--out", default=str(HERE / "results-sdk.json"))
    args = parser.parse_args()

    token = os.environ.get(args.token_env, "") if args.token_env else ""
    _TOKEN = token
    base = args.base_url.rstrip("/")

    results: dict[str, Any] = {
        "probe": "001-substrate-streamable-http/probe_sdk.py",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": base,
        "token_supplied": bool(token),
        "python": sys.version.split()[0],
        "versions": {pkg: md.version(pkg) for pkg in ("mcp", "httpx2")},
        "client_protocol_versions": {"handshake": list(HANDSHAKE_PROTOCOL_VERSIONS), "modern": list(MODERN_PROTOCOL_VERSIONS)},
        "cases": anyio.run(run_all, base, token),
    }
    results["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(args.out).write_text(json.dumps(redact(results), indent=2, default=str) + "\n")
    print("\n".join(redact(summarize(results["cases"]))))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
