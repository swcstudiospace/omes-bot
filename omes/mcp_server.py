"""Omes over MCP stdio: the tool registry as an MCP server.

`build_server` exposes registry tools (optionally roster-gated) to
MCP clients; `main` wires the default registry and serves stdio, so
`python -m omes.mcp_server` is the tool host a Grok Bot install (or
any MCP client) connects to. Policy and approval denials come back
as error results with the registry's own text; approval-gated tools
stay ungated only when the server was built with pre-approvals.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from omes.tools.coding import register_coding_tools
from omes.tools.discord import DiscordClient, register_discord_tools
from omes.tools.growth import register_growth_tools
from omes.tools.ide import register_ide_tools
from omes.tools.infra import InfraClient, InfraContext, register_infra_tools
from omes.tools.lead import LeadClient, LeadContext, register_lead_tools
from omes.tools.mobile import MobileClient, MobileContext, register_mobile_tools
from omes.tools.packs import PacksClient, PacksContext, register_packs_tools
from omes.tools.platform import register_platform_tools
from omes.tools.quality import QualityClient, QualityContext, register_quality_tools
from omes.tools.registry import ToolRegistry
from omes.tools.systems import SystemsClient, SystemsContext, register_systems_tools
from omes.tools.telegram import TelegramClient, register_telegram_tools
from omes.tools.ultrathink import (
    UltrathinkClient,
    UltrathinkContext,
    register_ultrathink_tools,
)
from omes.tools.webpack import WebClient, WebContext, register_web_tools
from omes.tools.x import XClient, register_x_tools

SERVER_NAME = "omes"
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


def default_registry(root: str | Path, home: str | Path) -> ToolRegistry:
    """Wire every family with safe defaults. Delegate needs a live agent: skipped.

    Credential-backed clients default to unconfigured and fail safe at
    call time; nothing here touches the network on its own.
    """
    registry = ToolRegistry()
    root = Path(root)
    home = Path(home)
    register_coding_tools(registry, root)
    register_growth_tools(registry, skills_root=root / "omes" / "skills",
                          memory_dir=root / "omes" / "memory",
                          session_db=root / "omes" / "sessions.db")
    register_platform_tools(registry, home=home)
    register_ide_tools(registry, root)
    register_x_tools(registry, XClient(transport=None))
    register_telegram_tools(registry, TelegramClient(make_bot=None, token=""))
    register_discord_tools(registry, DiscordClient(make_client=None, token=""))
    register_lead_tools(registry, LeadClient(LeadContext(root=root)))
    register_systems_tools(registry, SystemsClient(SystemsContext(root=root)))
    register_web_tools(registry, WebClient(WebContext(root=root)))
    register_mobile_tools(registry, MobileClient(MobileContext(root=root)))
    register_infra_tools(registry, InfraClient(InfraContext()))
    register_quality_tools(registry, QualityClient(QualityContext(root=root)))
    register_packs_tools(registry, PacksClient(PacksContext()))
    register_ultrathink_tools(registry, UltrathinkClient(UltrathinkContext()))
    return registry


def _mcp_tools(registry: ToolRegistry, roster: list[str] | None) -> list[Tool]:
    allowed = set(roster) if roster is not None else None
    out: list[Tool] = []
    for schema in registry.schemas():
        fn = schema.get("function", {})
        name = fn.get("name", "")
        if allowed is not None and name not in allowed:
            continue
        out.append(Tool(name=name, description=fn.get("description", ""),
                        inputSchema=fn.get("parameters", {"type": "object"})))
    return out


def list_tools_handler(registry: ToolRegistry, roster: list[str] | None = None):
    """MCP `tools/list` over the registry, optionally roster-gated."""
    from mcp.types import ListToolsResult

    tools = _mcp_tools(registry, roster)

    async def _list_tools(ctx: Any, params: Any) -> Any:
        return ListToolsResult(tools=tools)

    return _list_tools


def call_tool_handler(registry: ToolRegistry):
    """MCP `tools/call` through `registry.dispatch`."""

    async def _call_tool(ctx: Any, params: Any) -> Any:
        from mcp.types import CallToolResult

        payload = registry.dispatch(params.name, params.arguments or {})
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = {"output": payload}
        is_error = isinstance(decoded, dict) and "error" in decoded
        return CallToolResult(content=[TextContent(type="text", text=payload)],
                              isError=is_error)

    return _call_tool


def build_server(registry: ToolRegistry, roster: list[str] | None = None) -> Server:
    """Serve `registry` over MCP. `roster` limits the visible tools."""
    return Server(SERVER_NAME, version=SERVER_VERSION,
                  on_list_tools=list_tools_handler(registry, roster),
                  on_call_tool=call_tool_handler(registry))


async def _serve(server: Server) -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omes-mcp-server")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--no-roster", action="store_true",
                        help="serve every registered tool, not just the roster")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    roster: list[str] | None = None
    if not args.no_roster:
        roster_path = root / "omes" / "contracts" / "tool-rosters" / "omes.yaml"
        try:
            roster = roster_names(roster_path.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"omes-mcp-server: cannot read roster {roster_path}: {exc}", file=sys.stderr)
            return 2
    registry = default_registry(root, args.home)
    asyncio.run(_serve(build_server(registry, roster)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
