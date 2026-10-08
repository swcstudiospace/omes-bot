"""Omega Prime over MCP stdio: the tool registry as an MCP server.

`build_server` exposes registry tools (optionally roster-gated) to
MCP clients; `main` wires the default registry and serves stdio, so
`python -m omega_prime.mcp_server` is the tool host a Grok Bot install (or
any MCP client) connects to. Policy and approval denials come back
as error results with the registry's own text; approval-gated tools
stay ungated only when the server was built with pre-approvals.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import threading
import weakref
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from omega_prime.policy.policy import SeatPolicy
from omega_prime.providers.destination import DestinationTransport, SafeFetch
from omega_prime.substrate.client import DEFAULT_BASE_URL as SUBSTRATE_DEFAULT_URL
from omega_prime.substrate.client import SubstrateClient
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.coding import register_coding_tools
from omega_prime.tools.discord import DiscordClient, register_discord_tools
from omega_prime.tools.growth import register_growth_tools
from omega_prime.tools.ide import register_ide_tools
from omega_prime.tools.infra import InfraClient, InfraContext, register_infra_tools
from omega_prime.tools.lead import LeadClient, LeadContext, register_lead_tools
from omega_prime.tools.mobile import MobileClient, MobileContext, register_mobile_tools
from omega_prime.tools.packs import PacksClient, PacksContext, register_packs_tools
from omega_prime.tools.platform import register_platform_tools
from omega_prime.tools.quality import (
    QualityClient,
    QualityContext,
    register_quality_tools,
)
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.substrate_tools import register_substrate_tools
from omega_prime.tools.systems import (
    SystemsClient,
    SystemsContext,
    register_systems_tools,
)
from omega_prime.tools.telegram import TelegramClient, register_telegram_tools
from omega_prime.tools.ultrathink import (
    UltrathinkClient,
    UltrathinkContext,
    register_ultrathink_tools,
)
from omega_prime.tools.webpack import WebClient, WebContext, register_web_tools
from omega_prime.tools.x import XClient, register_x_tools

SERVER_NAME = "omega-prime"
SERVER_VERSION = "6.0.0"


def roster_names(text: str) -> list[str]:
    """Tool names under the `tools:` key of the roster YAML."""
    names: list[str] = []
    in_tools = False
    for line in text.splitlines():
        if line.startswith("tools:"):
            in_tools = True
            continue
        if not in_tools:
            continue
        if line.startswith("  - "):
            names.append(line[4:].strip())
            continue
        if line.strip() and not line.startswith(("#", " ")):
            break
    return names


class _UrllibXTransport:
    """Minimal X transport over urllib. Only built when a token is configured."""

    @staticmethod
    def _request(
        method: str,
        url: str,
        headers: dict,
        body: Any = None,
        params: dict | None = None,
    ) -> dict:
        import urllib.parse
        import urllib.request

        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}?{query}" if query else url
        data = json.dumps(body).encode("utf-8") if body is not None else None
        merged = dict(headers)
        if data is not None:
            merged.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(url, data=data, headers=merged, method=method)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def get(self, url: str, headers: dict, params: dict) -> dict:
        return self._request("GET", url, headers, params=params)

    def post(self, url: str, headers: dict, body: dict) -> dict:
        return self._request("POST", url, headers, body=body)


def _json_env(env: dict, name: str) -> dict:
    try:
        value = json.loads(env.get(name) or "")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def default_registry(
    root: str | Path,
    home: str | Path,
    *,
    policy: Any = None,
    approval_log: Any = None,
    env: dict | None = None,
) -> ToolRegistry:
    """Wire every family. Delegate needs a live agent: skipped.

    `policy` gates dispatch names and file writes; without it the
    registry keeps historical behavior. Coding tools root at
    `root/omega_prime` so the shipped read-only paths match. Connector credentials come
    from `env` (`X_API_TOKEN`, `TELEGRAM_BOT_TOKEN`,
    `DISCORD_BOT_TOKEN`, `ULTRATHINK_ROOT`, `OMEGA_PRIME_PACKS_JSON`,
    `OMEGA_PRIME_PACK_API_BASES_JSON`, `SUBSTRATE_URL`, `SUBSTRATE_TOKEN`,
    `SUBSTRATE_TOKEN_GROK_BOT`); missing values stay unconfigured
    and fail safe at call time.
    """
    env = dict(env or {})
    registry = ToolRegistry(approval_log=approval_log, policy=policy)
    root = Path(root)
    home = Path(home)
    legacy_root = root / "omes"
    target_root = root / "omega_prime"
    if legacy_root.is_dir():
        for item in ("memory", "skills", "sessions.db"):
            src = legacy_root / item
            dst = target_root / item
            if src.exists() and not dst.exists():
                try:
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                except Exception:
                    pass
    register_coding_tools(registry, root / "omega_prime", policy=policy)
    register_growth_tools(
        registry,
        skills_root=root / "omega_prime" / "skills",
        memory_dir=root / "omega_prime" / "memory",
        session_db=root / "omega_prime" / "sessions.db",
    )
    register_platform_tools(registry, home=home)
    register_ide_tools(registry, root)
    x_token = env.get("X_API_TOKEN", "")
    register_x_tools(
        registry,
        XClient(transport=_UrllibXTransport() if x_token else None, token=x_token),
    )
    register_telegram_tools(
        registry, TelegramClient(make_bot=None, token=env.get("TELEGRAM_BOT_TOKEN", ""))
    )
    register_discord_tools(
        registry,
        DiscordClient(make_client=None, token=env.get("DISCORD_BOT_TOKEN", "")),
    )
    register_lead_tools(registry, LeadClient(LeadContext(root=root)))
    register_systems_tools(registry, SystemsClient(SystemsContext(root=root)))
    transport = DestinationTransport(policy)
    safe_fetch = SafeFetch(transport)
    web_ctx = WebContext(
        root=root, policy=policy, transport=transport, fetch=safe_fetch
    )
    register_web_tools(registry, WebClient(web_ctx))
    bind_dispatch_transport(registry, transport)
    register_mobile_tools(registry, MobileClient(MobileContext(root=root)))
    register_infra_tools(registry, InfraClient(InfraContext()))
    register_quality_tools(registry, QualityClient(QualityContext(root=root)))
    register_packs_tools(
        registry,
        PacksClient(
            PacksContext(
                packs=_json_env(env, "OMEGA_PRIME_PACKS_JSON"),
                api_bases=_json_env(env, "OMEGA_PRIME_PACK_API_BASES_JSON"),
            )
        ),
    )
    register_ultrathink_tools(
        registry,
        UltrathinkClient(UltrathinkContext(root=env.get("ULTRATHINK_ROOT", ""))),
    )
    register_substrate_tools(
        registry,
        SubstrateClient(
            env.get("SUBSTRATE_URL", "") or SUBSTRATE_DEFAULT_URL,
            token=env.get("SUBSTRATE_TOKEN", "")
            or env.get("SUBSTRATE_TOKEN_GROK_BOT", "")
            or None,
        ),
    )
    # Prime capability families are config-gated (default off): a disabled
    # family is not registered and is absent from the offered roster (LOOP-05).
    # RLM needs a live parent agent, so registration happens where the agent's
    # registry is built (the delegate_task precedent: skipped here).
    return registry


_BOUND_TRANSPORTS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_BOUND_TRANSPORTS_LOCK = threading.Lock()

_DISPATCH_ROOT_TOOLS = (
    "web_preview_check",
    "web_review_page",
    "browser_navigate",
    "browser_snapshot",
)

_DISPATCH_DEADLINES = {
    "web_preview_check": 15.0,
    "browser_snapshot": 15.0,
    "web_review_page": 60.0,
    "browser_navigate": 60.0,
}


class _SerialCoordinator:
    """Serial dispatch gate for one registry's shared transport."""

    def __init__(self, transport: DestinationTransport) -> None:
        self.transport = transport
        self.lock = threading.Lock()
        self.pending = 0


def _coordinator_for(registry: ToolRegistry) -> _SerialCoordinator | None:
    with _BOUND_TRANSPORTS_LOCK:
        return _BOUND_TRANSPORTS.get(registry)


def bind_dispatch_transport(
    registry: ToolRegistry, transport: DestinationTransport
) -> None:
    """Bind one shared transport to a registry's dispatch path."""
    with _BOUND_TRANSPORTS_LOCK:
        existing = _BOUND_TRANSPORTS.get(registry)
        if existing is not None:
            if existing.transport is not transport:
                raise ValueError("registry is already bound to a different transport")
            return
        _BOUND_TRANSPORTS[registry] = _SerialCoordinator(transport)
    inner = registry.dispatch

    def _bound_dispatch(name: str, arguments: Any = None) -> str:
        if name not in _DISPATCH_ROOT_TOOLS:
            return inner(name, arguments)
        coordinator = _coordinator_for(registry)
        if coordinator is None or coordinator.transport is not transport:
            return json.dumps(
                {"error": "not_configured: no preview transport is bound"}
            )
        with coordinator.lock:
            if coordinator.pending >= 16:
                return json.dumps({"error": "upstream_error: dispatch queue is full"})
            coordinator.pending += 1
        try:
            cap = _DISPATCH_DEADLINES.get(name, 15.0)
            try:
                root = transport.begin_operation(
                    deadline_at=transport._clock.monotonic() + cap
                )
            except Exception:
                return json.dumps({"error": "upstream_error: cannot begin operation"})
            if root.abort_handle.reason is not None:
                transport.finish_operation(
                    root, deadline_at=transport._clock.monotonic() + 5.0
                )
                return json.dumps({"error": "upstream_error: operation was cancelled"})
            binding = transport.bind_operation(root)
            with binding:
                payload = inner(name, arguments)
            drain = transport.finish_operation(
                root, deadline_at=transport._clock.monotonic() + 5.0
            )
            if not drain.complete:
                return json.dumps(
                    {
                        "error": f"upstream_error: operation drain incomplete (pending={drain.pending_scopes}, abort={drain.abort_reason})"
                    }
                )
            return payload
        finally:
            with coordinator.lock:
                coordinator.pending -= 1

    registry.dispatch = _bound_dispatch  # type: ignore[method-assign]


def _mcp_tools(registry: ToolRegistry, roster: list[str] | None) -> list[Tool]:
    allowed = set(roster) if roster is not None else None
    out: list[Tool] = []
    for schema in registry.schemas():
        fn = schema.get("function", {})
        name = fn.get("name", "")
        if allowed is not None and name not in allowed:
            continue
        out.append(
            Tool(
                name=name,
                description=fn.get("description", ""),
                input_schema=fn.get("parameters", {"type": "object"}),
            )
        )
    return out


def list_tools_handler(registry: ToolRegistry, roster: list[str] | None = None):
    """MCP `tools/list` over the registry, optionally roster-gated."""
    from mcp.types import ListToolsResult

    tools = _mcp_tools(registry, roster)

    async def _list_tools(ctx: Any, params: Any) -> Any:
        return ListToolsResult(tools=tools)

    return _list_tools


def call_tool_handler(registry: ToolRegistry, roster: list[str] | None = None):
    """MCP `tools/call` through `registry.dispatch`, roster-enforced."""

    allowed = set(roster) if roster is not None else None

    async def _call_tool(ctx: Any, params: Any) -> Any:
        from mcp.types import CallToolResult

        if allowed is not None and params.name not in allowed:
            payload = json.dumps(
                {"error": f"policy forbids {params.name}", "tool": params.name}
            )
        else:
            payload = registry.dispatch(params.name, params.arguments or {})
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = {"output": payload}
        is_error = isinstance(decoded, dict) and "error" in decoded
        return CallToolResult(
            content=[TextContent(type="text", text=payload)], is_error=is_error
        )

    return _call_tool


def build_server(registry: ToolRegistry, roster: list[str] | None = None) -> Server:
    """Serve `registry` over MCP. `roster` limits listing and calling."""
    return Server(
        SERVER_NAME,
        version=SERVER_VERSION,
        on_list_tools=list_tools_handler(registry, roster),
        on_call_tool=call_tool_handler(registry, roster),
    )


async def _serve(server: Server) -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omega-prime-mcp-server")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument(
        "--no-roster",
        action="store_true",
        help="serve every registered tool, not just the roster",
    )
    parser.add_argument(
        "--approve",
        action="append",
        default=[],
        metavar="TOOL:APPROVER",
        help="pre-approve one gated tool (repeatable)",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    roster: list[str] | None = None
    if not args.no_roster:
        roster_path = (
            root / "omega_prime" / "contracts" / "tool-rosters" / "omega-prime.yaml"
        )
        try:
            roster = roster_names(roster_path.read_text(encoding="utf-8"))
        except OSError as exc:
            print(
                f"omega-prime-mcp-server: cannot read roster {roster_path}: {exc}",
                file=sys.stderr,
            )
            return 2
    try:
        policy = SeatPolicy.load(
            root / "omega_prime" / "contracts" / "policies" / "omega-prime.json"
        )
    except (OSError, ValueError) as exc:
        print(
            f"omega-prime-mcp-server: cannot load seat policy: {exc}", file=sys.stderr
        )
        return 2
    log = ApprovalLog()
    for item in args.approve:
        tool, _, approver = item.partition(":")
        if not tool or not approver:
            print(
                f"omega-prime-mcp-server: bad --approve {item!r}, want TOOL:APPROVER",
                file=sys.stderr,
            )
            return 2
        outcome = log.approve(tool, approver)
        if not outcome.get("approved"):
            print(
                f"omega-prime-mcp-server: cannot pre-approve {tool}: {outcome.get('error')}",
                file=sys.stderr,
            )
            return 2
    registry = default_registry(
        root, args.home, policy=policy, approval_log=log, env=dict(os.environ)
    )
    asyncio.run(_serve(build_server(registry, roster)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
