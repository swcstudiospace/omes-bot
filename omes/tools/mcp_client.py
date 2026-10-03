"""One-shot MCP client: one JSON-RPC line in, one JSON line out.

Adapted from Hermes ``tools/mcp_tool.py``. There is no MCP SDK and no long-lived
session. ``command`` is an argv list. A string is refused and starts nothing.
On timeout the child is killed.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any


def mcp_call(
    command: Any,
    tool: Any,
    arguments: Any,
    *,
    cwd: str | Path,
    timeout: float = 5,
) -> dict[str, Any]:
    """Spawn ``command`` in ``cwd`` and call ``tool`` with one JSON-RPC line.

    Stdin is ``tools/call``. A successful process returns ``{"result": ...}``.
    Invalid JSON or a non-zero exit returns an error. A timeout returns an
    error, the captured streams, and a non-zero exit code.
    """
    if isinstance(command, str):
        return {"error": "command must be an argv list, not a string"}
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or part == "" for part in command)
    ):
        return {"error": "command must be a non-empty argv list of strings"}
    if not isinstance(tool, str) or tool == "":
        return {"error": "tool must be a non-empty string"}
    if not isinstance(arguments, dict):
        return {"error": "arguments must be an object"}
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        return {"error": "timeout must be a positive number of seconds"}
    root = Path(cwd)
    if not root.is_dir():
        return {"error": f"cwd is not a directory: {cwd}"}
    try:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return {"error": "arguments are not JSON-serializable"}
    return _run(command, cwd=root, timeout=timeout, stdin=(payload + "\n").encode("utf-8"))


def _run(argv: list[str], *, cwd: Path, timeout: float, stdin: bytes) -> dict[str, Any]:
    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    try:
        stdout, stderr = proc.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        stdout, stderr, code = _kill(proc)
        return {
            "error": f"timed out after {timeout} seconds",
            "stdout": _text(stdout),
            "stderr": _text(stderr),
            "exit_code": code,
        }
    return _message(stdout, proc.returncode)


def _message(stdout: bytes | None, code: int | None) -> dict[str, Any]:
    if code != 0:
        return {"error": f"MCP server exited {code}"}
    lines = _text(stdout).splitlines()
    line = lines[0] if lines else ""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return {"error": "invalid JSON from the MCP server"}
    if not isinstance(message, dict) or "result" not in message:
        return {"error": "MCP response has no result"}
    return {"result": message["result"]}


def _kill(proc: subprocess.Popen[bytes]) -> tuple[bytes, bytes, int]:
    """SIGKILL the child's process group, then reap it. The exit is non-zero."""
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        stdout, stderr = proc.communicate(timeout=5)
    code = proc.returncode
    if code in (None, 0):
        code = 124
    return stdout or b"", stderr or b"", code


def _text(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    return data.decode("utf-8", errors="replace")


__all__ = ["mcp_call"]
