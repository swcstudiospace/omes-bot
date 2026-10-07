"""Register the local platform tools on one registry.

``execute_code`` and ``mcp_call`` close over ``home``. The browser tools close
over ``browser`` and do not open a socket when it is missing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from omes.tools.browser import BrowserSession
from omes.tools.execute import execute_code as run_execute_code
from omes.tools.mcp_client import mcp_call as run_mcp_call
from omes.tools.registry import ToolRegistry

# Offered after delegate_task. omes/contracts/tool-rosters/omes.yaml lists these.
PLATFORM_TOOL_NAMES = (
    "execute_code",
    "mcp_call",
    "browser_navigate",
    "browser_snapshot",
)


def register_platform_tools(
    registry: ToolRegistry,
    *,
    home: str | Path,
    browser: BrowserSession | None = None,
) -> list[str]:
    """Register the four platform tools. The model does not send ``home``."""

    def execute_code(code: str, timeout: float = 5) -> dict[str, Any]:
        return run_execute_code(code, home=home, timeout=timeout)

    def mcp_call(
        command: Any,
        tool: str,
        arguments: dict,
        timeout: float = 5,
    ) -> dict[str, Any]:
        return run_mcp_call(command, tool, arguments, cwd=home, timeout=timeout)

    def browser_navigate(url: str) -> dict[str, Any]:
        if browser is None:
            return {"error": "browser is not available"}
        return browser.browser_navigate(url)

    def browser_snapshot() -> dict[str, Any]:
        if browser is None:
            return {"error": "browser is not available"}
        return browser.browser_snapshot()

    handlers: dict[str, Callable[..., Any]] = {
        "execute_code": execute_code,
        "mcp_call": mcp_call,
        "browser_navigate": browser_navigate,
        "browser_snapshot": browser_snapshot,
    }
    if tuple(handlers) != PLATFORM_TOOL_NAMES:
        raise RuntimeError("platform tool handlers drifted from PLATFORM_TOOL_NAMES")
    for name in PLATFORM_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name])
    return list(PLATFORM_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "execute_code": (
        "Run Python source in a short-lived local process whose working directory is the bot home. "
        "Empty code is refused. A timeout kills the process.",
        _object(
            {
                "code": _string(
                    "Python source. Empty source is an error and starts nothing."
                ),
                "timeout": {
                    "type": "number",
                    "description": "Seconds before the process is killed. Default is 5.",
                },
            },
            ["code"],
        ),
    ),
    "mcp_call": (
        "Call one MCP tool by spawning an argv and exchanging a single JSON-RPC line. "
        "command is an argument list, not a shell string.",
        _object(
            {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Argv of the MCP server. A string is an error and starts nothing.",
                },
                "tool": _string("Tool name to pass as params.name."),
                "arguments": {
                    "type": "object",
                    "description": "Arguments object passed to the MCP tool.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Seconds before the process is killed. Default is 5.",
                },
            },
            ["command", "tool", "arguments"],
        ),
    ),
    "browser_navigate": (
        "Open a URL through the injected browser transport and return the page text. "
        "No socket is opened. A missing browser is an error.",
        _object(
            {"url": _string("URL the transport should open.")},
            ["url"],
        ),
    ),
    "browser_snapshot": (
        "Return the injected browser transport's current page text. "
        "No socket is opened. A missing browser is an error.",
        _object({}, []),
    ),
}


__all__ = ["PLATFORM_TOOL_NAMES", "register_platform_tools"]
