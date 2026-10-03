"""Session MCP client on the official SDK: initialize, then tools/call.

Beside the one-shot ``mcp_call`` (one ``tools/call`` line, no handshake).
Use this for servers that require the initialize handshake. The safety
contract matches the one-shot client: ``command`` is an argv list, a string
is refused and starts nothing, and on timeout the child is reaped.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def mcp_session_call(
    command: Any,
    tool: Any,
    arguments: Any,
    *,
    cwd: str | Path,
    timeout: float = 5,
) -> dict[str, Any]:
    """Spawn ``command`` in ``cwd`` and call ``tool`` over an SDK session.

    Opens a stdio session, runs ``initialize()`` plus ``call_tool``, and
    returns ``{"result": ...}`` with JSON-safe content blocks. A tool-level
    error returns both ``error`` and ``result``. Refusals, spawn failures,
    and timeouts return ``error`` only.
    """
    refusal = _validate(command, tool, arguments, cwd, timeout)
    if refusal is not None:
        return {"error": refusal}
    assert isinstance(command, list)
    try:
        return asyncio.run(_call(command, tool, arguments, Path(cwd), timeout))
    except TimeoutError:
        return {"error": f"timed out after {timeout} seconds"}
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:  # noqa: BLE001 - SDK failures become error dicts
        message = str(exc) or type(exc).__name__
        return {"error": f"{type(exc).__name__}: {message}"}


def _validate(command: Any, tool: Any, arguments: Any, cwd: Any, timeout: Any) -> str | None:
    if isinstance(command, str):
        return "command must be an argv list, not a string"
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or part == "" for part in command)
    ):
        return "command must be a non-empty argv list of strings"
    if not isinstance(tool, str) or tool == "":
        return "tool must be a non-empty string"
    if not isinstance(arguments, dict):
        return "arguments must be an object"
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        return "timeout must be a positive number of seconds"
    if not Path(cwd).is_dir():
        return f"cwd is not a directory: {cwd}"
    return None


async def _call(
    command: list[str], tool: str, arguments: dict, cwd: Path, timeout: float
) -> dict[str, Any]:
    async def _session() -> dict[str, Any]:
        params = StdioServerParameters(
            command=command[0], args=command[1:], cwd=str(cwd)
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
        return _shape(result)

    try:
        return await asyncio.wait_for(_session(), timeout)
    except asyncio.TimeoutError:
        raise TimeoutError from None


def _shape(result: Any) -> dict[str, Any]:
    dump = result.model_dump(mode="json", exclude_none=True)
    failed = dump.get("is_error", dump.get("isError", False))
    if not failed:
        return {"result": dump}
    texts = [
        block.get("text")
        for block in dump.get("content", [])
        if isinstance(block, dict) and block.get("text")
    ]
    error = texts[0] if texts else "MCP tool reported an error"
    return {"error": error, "result": dump}


__all__ = ["mcp_session_call"]
