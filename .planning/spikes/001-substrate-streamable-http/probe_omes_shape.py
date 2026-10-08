#!/usr/bin/env python3
"""Spike 001 (a): how Omes's current SubstrateClient request shape fares on substrate-mcp.

Part 1 (raw, stdlib only) replays the exact bytes ``HttpTransport.post`` sends for
``SubstrateClient._mcp_post`` (Content-Type + Content-Length, no Accept, a bare
``tools/call`` with no ``initialize``) plus controlled variants, and records status,
content-type and body for each.

Part 2 (needs the repo's .venv) imports ``SubstrateClient`` read-only and calls only
read-only methods: health, brief, memory_search, docs_search, and the private
``_call_tool`` / ``_call_tool_text`` with ``graph_get``. It never calls memory_write,
emit, graph_claim, graph_release, graph_complete or graph_heartbeat.

Part 3 (needs the repo's .venv) answers "what if Omes only added the Accept header and
decoded SSE?": it feeds real server responses through an in-probe shim transport into
the unmodified ``SubstrateClient`` and shows how ``isError`` results are treated.

Every request here is read-only on the substrate. Tokens are read from the env var
named by --token-env (never printed) and redacted from all output.

    python3 probe_omes_shape.py                        # part 1 only (any python3)
    ../../../.venv/bin/python probe_omes_shape.py      # parts 1-3
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DUMMY_GRAPH = "ut-spike001-00000000"
BODY_LIMIT = 2000

_TOKEN = ""


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(_TOKEN, "[REDACTED]") if _TOKEN else value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def shown_headers(headers: dict) -> dict:
    out = dict(headers)
    if "Authorization" in out:
        out["Authorization"] = "Bearer [REDACTED]"
    return out


def parse_sse(text: str) -> list[Any]:
    """JSON payloads of every SSE ``data:`` event in ``text``."""
    events, data = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
        elif line == "" and data:
            joined = "\n".join(data)
            data = []
            try:
                events.append(json.loads(joined))
            except json.JSONDecodeError:
                events.append({"_unparsed": joined[:BODY_LIMIT]})
    return events


def raw_request(base: str, method: str, path: str, headers: dict, body: Any = None) -> dict:
    """One request on a fresh stdlib connection, like HttpTransport._request."""
    parts = urlsplit(base)
    payload = None if body is None else json.dumps(body).encode("utf-8")
    sent = dict(headers)
    if payload is not None:
        sent.setdefault("Content-Type", "application/json")
        sent["Content-Length"] = str(len(payload))
    record: dict[str, Any] = {
        "request": {
            "method": method,
            "path": path,
            "headers": shown_headers(sent),
            "body": body,
            "note": "http.client also adds Host and Accept-Encoding: identity",
        }
    }
    start = time.monotonic()
    conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=15)
    try:
        conn.request(method, path, body=payload, headers=sent)
        resp = conn.getresponse()
        raw = resp.read()
        text = raw.decode("utf-8", "replace")
        record["response"] = {
            "status": resp.status,
            "reason": resp.reason,
            "content_type": resp.getheader("content-type"),
            "mcp_session_id": resp.getheader("mcp-session-id"),
            "allow": resp.getheader("allow"),
            "body": text[:BODY_LIMIT],
            "body_truncated": len(text) > BODY_LIMIT,
        }
        ctype = (resp.getheader("content-type") or "").lower()
        if ctype.startswith("text/event-stream"):
            record["response"]["sse_events"] = parse_sse(text)
        elif ctype.startswith("application/json") and text:
            try:
                record["response"]["json"] = json.loads(text)
            except json.JSONDecodeError:
                pass
        # What HttpTransport.post would do with this response.
        record["omes_http_transport_verdict"] = transport_verdict(resp.status, text)
    except Exception as exc:  # noqa: BLE001 - the probe records every failure
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        conn.close()
    record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    return record


def transport_verdict(status: int, text: str) -> str:
    """Mirror omes.providers.http._check_status + _once JSON decoding."""
    if status in (408, 429) or 500 <= status <= 599:
        return f"retryable -> after retries: ProviderError('request to <host> failed after retries: HTTP {status}')"
    if 400 <= status <= 499:
        return f"ProviderError('HTTP {status} from <url>') (final, no retry)"
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        return f"ProviderError('response is not JSON: {exc}')"
    if not isinstance(decoded, dict):
        return "ProviderError('response is not a JSON object')"
    return "decoded JSON object returned to SubstrateClient"


def envelope(rpc_id: int, method: str, params: dict | None = None) -> dict:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def tools_call(rpc_id: int, name: str, arguments: dict) -> dict:
    return envelope(rpc_id, "tools/call", {"name": name, "arguments": arguments})


INITIALIZE_PARAMS = {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {"name": "spike-001-raw", "version": "0"},
}

BOTH = "application/json, text/event-stream"


def part1_raw(base: str, auth: dict) -> list[dict]:
    cases = [
        ("A01 GET /healthz (Omes health() headers)", "GET", "/healthz", {"Accept": "application/json", **auth}, None),
        ("A02 POST /mcp exact Omes _mcp_post shape: tools/call graph_get, no Accept", "POST", "/mcp", dict(auth), tools_call(1, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A03 same, Accept: application/json only", "POST", "/mcp", {"Accept": "application/json", **auth}, tools_call(2, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A04 same, Accept: text/event-stream only", "POST", "/mcp", {"Accept": "text/event-stream", **auth}, tools_call(3, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A05 same, Accept both (spec-compliant), still no initialize", "POST", "/mcp", {"Accept": BOTH, **auth}, tools_call(4, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A06 Accept both, tools/call memory_brief", "POST", "/mcp", {"Accept": BOTH, **auth}, tools_call(5, "memory_brief", {"repo": "spike/omega-001"})),
        ("A07 Accept both, tools/call graph_get with missing graph_id (isError expected)", "POST", "/mcp", {"Accept": BOTH, **auth}, tools_call(6, "graph_get", {})),
        ("A08 Accept both, tools/call unknown tool (isError expected)", "POST", "/mcp", {"Accept": BOTH, **auth}, tools_call(7, "no_such_tool", {})),
        ("A09 Accept both, initialize", "POST", "/mcp", {"Accept": BOTH, **auth}, envelope(8, "initialize", INITIALIZE_PARAMS)),
        ("A10 Accept both, tools/list", "POST", "/mcp", {"Accept": BOTH, "MCP-Protocol-Version": "2025-11-25", **auth}, envelope(9, "tools/list", {})),
        ("A11 Accept both, server/discover with MCP-Protocol-Version 2026-07-28 (what SDK v2 auto mode probes)", "POST", "/mcp", {"Accept": BOTH, "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "server/discover", **auth}, envelope(10, "server/discover", {})),
        ("A12 Accept both, tools/call with MCP-Protocol-Version 2026-07-28", "POST", "/mcp", {"Accept": BOTH, "MCP-Protocol-Version": "2026-07-28", **auth}, tools_call(11, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A13 Accept both, Content-Type text/plain", "POST", "/mcp", {"Accept": BOTH, "Content-Type": "text/plain", **auth}, tools_call(12, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A14 GET /mcp (server-initiated SSE stream)", "GET", "/mcp", {"Accept": "text/event-stream", **auth}, None),
        ("A15 DELETE /mcp (session termination)", "DELETE", "/mcp", dict(auth), None),
        ("A16 Accept both, bogus bearer token", "POST", "/mcp", {"Accept": BOTH, "Authorization": "Bearer spike-001-bogus-token"}, tools_call(13, "graph_get", {"graph_id": DUMMY_GRAPH})),
        ("A17 GET /healthz with no Authorization header", "GET", "/healthz", {"Accept": "application/json"}, None),
        ("A18 POST /mcp with no Authorization header, Accept both", "POST", "/mcp", {"Accept": BOTH}, tools_call(14, "graph_get", {"graph_id": DUMMY_GRAPH})),
    ]
    results = []
    for name, method, path, headers, body in cases:
        rec = raw_request(base, method, path, headers, body)
        rec["case"] = name
        results.append(rec)
    return results


class SseShimTransport:
    """Part 3 only: HttpTransport.post plus Accept-both and SSE decoding.

    Lives in this probe, never in omes. It answers "would fixing only the Accept
    header and the SSE framing make the current client correct?".
    """

    def __init__(self, base: str) -> None:
        self._base = base

    def post(self, url: str, headers: dict, body: dict) -> dict:
        path = urlsplit(url).path
        rec = raw_request(self._base, "POST", path, {"Accept": BOTH, **(headers or {})}, body)
        resp = rec.get("response") or {}
        if resp.get("status") != 200:
            raise RuntimeError(f"HTTP {resp.get('status')} {resp.get('body', '')[:200]}")
        for event in resp.get("sse_events") or []:
            if isinstance(event, dict) and event.get("id") == body.get("id"):
                return event
        if "json" in resp:
            return resp["json"]
        raise RuntimeError("no JSON-RPC response for this id in the SSE stream")


def capture(fn, *args, **kwargs) -> dict:
    start = time.monotonic()
    try:
        value = fn(*args, **kwargs)
        out = {"outcome": "returned", "type": type(value).__name__, "value": value}
        if isinstance(value, str) and len(value) > BODY_LIMIT:
            out["value"] = value[:BODY_LIMIT]
            out["value_truncated"] = True
    except Exception as exc:  # noqa: BLE001
        out = {"outcome": "raised", "exception": f"{type(exc).__module__}.{type(exc).__name__}", "message": str(exc)}
        if exc.__cause__ is not None:
            out["cause"] = f"{type(exc.__cause__).__name__}: {exc.__cause__}"
    out["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    return out


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def import_omes():
    sys.dont_write_bytecode = True  # never write __pycache__ into the repo tree
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from omes.providers.http import HttpTransport
    from omes.substrate.client import SubstrateClient

    return SubstrateClient, HttpTransport


def part2_client(base: str, token: str | None) -> dict:
    try:
        SubstrateClient, HttpTransport = import_omes()
    except Exception as exc:  # noqa: BLE001
        return {"skipped": f"cannot import omes ({type(exc).__name__}: {exc}); run with the repo .venv python"}
    out: dict[str, Any] = {}
    client = SubstrateClient(base, token=token, transport=HttpTransport(timeout=5.0))
    out["B01 health() [default retries=2]"] = capture(client.health)
    out["B02 brief(repo=...) [REST, fail-open]"] = capture(client.brief, repo="spike/omega-001")
    out["B03 _call_tool('graph_get', dummy)"] = capture(client._call_tool, "graph_get", {"graph_id": DUMMY_GRAPH})
    out["B04 _call_tool_text('graph_get', dummy)"] = capture(client._call_tool_text, "graph_get", {"graph_id": DUMMY_GRAPH})
    out["B05 memory_search('spike-001-probe') [fail-open]"] = capture(client.memory_search, "spike-001-probe")
    out["B06 docs_search('spike-001-probe') [raises]"] = capture(client.docs_search, "spike-001-probe")
    down = f"http://127.0.0.1:{free_port()}"
    down_client = SubstrateClient(down, token=token, transport=HttpTransport(timeout=5.0))
    out["B07 substrate down: _call_tool('graph_get') against a closed port"] = capture(down_client._call_tool, "graph_get", {"graph_id": DUMMY_GRAPH})
    out["B08 substrate down: memory_search [fail-open]"] = capture(down_client.memory_search, "spike-001-probe")
    return out


def part3_shim(base: str, token: str | None) -> dict:
    try:
        SubstrateClient, _ = import_omes()
    except Exception as exc:  # noqa: BLE001
        return {"skipped": f"cannot import omes ({type(exc).__name__}: {exc}); run with the repo .venv python"}
    client = SubstrateClient(base, token=token, transport=SseShimTransport(base))
    return {
        "C01 _call_tool('graph_get', dummy)": capture(client._call_tool, "graph_get", {"graph_id": DUMMY_GRAPH}),
        "C02 _call_tool_text('graph_get', dummy)": capture(client._call_tool_text, "graph_get", {"graph_id": DUMMY_GRAPH}),
        "C03 _call_tool('graph_get', {}) -> server isError": capture(client._call_tool, "graph_get", {}),
        "C04 _call_tool_text('graph_get', {}) -> server isError": capture(client._call_tool_text, "graph_get", {}),
        "C05 _call_tool_text('no_such_tool', {}) -> server isError": capture(client._call_tool_text, "no_such_tool", {}),
        "C06 memory_search('spike-001-probe')": capture(client.memory_search, "spike-001-probe"),
    }


def summarize(raw: list[dict]) -> list[str]:
    lines = []
    for rec in raw:
        resp = rec.get("response") or {}
        status = resp.get("status", "ERR")
        ctype = resp.get("content_type")
        lines.append(f"{status!s:>4}  {ctype or '-':<40}  {rec['case']}")
    return lines


def main() -> int:
    global _TOKEN
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:7410")
    parser.add_argument("--token-env", default=None, help="env var holding a bearer token (never printed)")
    parser.add_argument("--out", default=str(HERE / "results-omes-shape.json"))
    parser.add_argument("--raw-only", action="store_true", help="skip parts 2-3 (no omes import)")
    args = parser.parse_args()

    token = os.environ.get(args.token_env, "") if args.token_env else ""
    _TOKEN = token
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    base = args.base_url.rstrip("/")

    results: dict[str, Any] = {
        "probe": "001-substrate-streamable-http/probe_omes_shape.py",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": base,
        "token_supplied": bool(token),
        "python": sys.version.split()[0],
        "part1_raw": part1_raw(base, auth),
    }
    if not args.raw_only:
        results["part2_substrate_client"] = part2_client(base, token or None)
        results["part3_sse_shim_with_unmodified_client"] = part3_shim(base, token or None)
    results["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    Path(args.out).write_text(json.dumps(redact(results), indent=2, default=str) + "\n")
    print("\n".join(redact(summarize(results["part1_raw"]))))
    for part in ("part2_substrate_client", "part3_sse_shim_with_unmodified_client"):
        for name, rec in (results.get(part) or {}).items():
            if not isinstance(rec, dict):
                print(f"{part}: {redact(rec)}")
                continue
            detail = rec.get("message") if rec.get("outcome") == "raised" else repr(rec.get("value"))[:160]
            print(redact(f"{rec.get('outcome', '-'):>8}  {name}: {detail}"))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
