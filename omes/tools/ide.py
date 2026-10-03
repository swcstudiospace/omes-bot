"""Register the IDE tools on one registry, rooted at one directory.

``lsp_diagnostics`` opens one document on a language server spawned from an
argv command and returns its diagnostics. ``dap_stop`` launches one program
under a debug adapter spawned the same way, stops on one breakpoint line,
and reports the stop. Both servers are fixture scripts in tests; no real
language server or adapter ships here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omes.tools.dap import DapSession
from omes.tools.file_ops import FileWorkspace
from omes.tools.lsp import LspSession
from omes.tools.registry import ToolRegistry
from omes.tools.rpc import RpcConnection

# Offered after the platform names. omes/contracts/tool-rosters/omes.yaml lists these.
IDE_TOOL_NAMES = (
    "lsp_diagnostics",
    "dap_stop",
)


def register_ide_tools(registry: ToolRegistry, root: str | Path) -> list[str]:
    """Register both IDE tools. ``root`` jails every path the model sends."""
    workspace = FileWorkspace(root)
    root_path = workspace.root

    def lsp_diagnostics(
        command: Any,
        path: str,
        language_id: str = "python",
        timeout: float = 10,
    ) -> dict[str, Any]:
        argv_error = _check_command(command)
        if argv_error is not None:
            return {"error": argv_error}
        if not isinstance(language_id, str) or language_id == "":
            return {"error": "language_id must be a non-empty string"}
        timeout_error = _check_timeout(timeout)
        if timeout_error is not None:
            return {"error": timeout_error}
        read = workspace.read_file(path)
        if "error" in read:
            return read
        connection = RpcConnection(command, cwd=str(root_path), timeout=timeout)
        session = LspSession(connection)
        try:
            session.start(str(root_path), timeout=timeout)
            uri = session.open_document(
                str(root_path / read["path"]), language_id, read["content"]
            )
            found = session.diagnostics(uri, timeout=timeout)
        except (TimeoutError, EOFError, ValueError, RuntimeError) as exc:
            return {"error": f"lsp session failed: {exc}"}
        finally:
            try:
                session.shutdown(timeout=timeout)
            except Exception:
                pass
            connection.close()
        return {"path": read["path"], "diagnostics": found}

    def dap_stop(
        command: Any, path: str, line: int, timeout: float = 10
    ) -> dict[str, Any]:
        argv_error = _check_command(command)
        if argv_error is not None:
            return {"error": argv_error}
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            return {"error": "line must be a positive integer"}
        timeout_error = _check_timeout(timeout)
        if timeout_error is not None:
            return {"error": timeout_error}
        read = workspace.read_file(path)
        if "error" in read:
            return read
        program = str(root_path / read["path"])
        connection = RpcConnection(command, cwd=str(root_path), timeout=timeout)
        session = DapSession(connection)
        try:
            session.start(timeout=timeout)
            session.launch(program, timeout=timeout)
            breakpoints = session.set_breakpoints(program, [line], timeout=timeout)
            session.configuration_done(timeout=timeout)
            stopped = session.wait_stopped(timeout=timeout)
            thread_id = stopped.get("threadId", 1)
            frames: list[dict[str, Any]] = []
            if isinstance(thread_id, int):
                for frame in session.stack_trace(thread_id, timeout=timeout):
                    if not isinstance(frame, dict):
                        continue
                    frames.append(
                        {"name": frame.get("name"), "line": frame.get("line")}
                    )
        except (TimeoutError, EOFError, ValueError, RuntimeError) as exc:
            return {"error": f"dap session failed: {exc}"}
        finally:
            try:
                session.disconnect(timeout=timeout)
            except Exception:
                connection.close()
        return {
            "stopped": True,
            "reason": stopped.get("reason"),
            "thread_id": stopped.get("threadId"),
            "frames": frames,
            "breakpoints": breakpoints,
        }

    handlers = {
        "lsp_diagnostics": lsp_diagnostics,
        "dap_stop": dap_stop,
    }
    if set(handlers) != set(IDE_TOOL_NAMES):
        raise RuntimeError("IDE tool handlers drifted from IDE_TOOL_NAMES")
    for name in IDE_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name])
    return list(IDE_TOOL_NAMES)


def _check_command(command: Any) -> str | None:
    if isinstance(command, str):
        return "command must be an argv list, not a string"
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or part == "" for part in command)
    ):
        return "command must be a non-empty argv list of strings"
    return None


def _check_timeout(timeout: Any) -> str | None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        return "timeout must be a positive number of seconds"
    return None


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "lsp_diagnostics": (
        "Ask a spawned language server for one file's diagnostics inside the workspace root. "
        "The command is an argv list that speaks LSP over stdio. Returns the diagnostics.",
        _object(
            {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Argv that spawns the language server. A string is an error.",
                },
                "path": _string("File to open, relative to the workspace root or absolute inside it."),
                "language_id": _string("LSP language id. Defaults to python."),
                "timeout": {"type": "number", "description": "Seconds per wait. Defaults to 10."},
            },
            ["command", "path"],
        ),
    ),
    "dap_stop": (
        "Launch one file under a spawned debug adapter, stop on one breakpoint line, "
        "and report the stop with its stack frames. The command is an argv list that "
        "speaks DAP over stdio.",
        _object(
            {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Argv that spawns the debug adapter. A string is an error.",
                },
                "path": _string("Program to launch, relative to the workspace root or absolute inside it."),
                "line": {"type": "integer", "description": "1-based breakpoint line."},
                "timeout": {"type": "number", "description": "Seconds per wait. Defaults to 10."},
            },
            ["command", "path", "line"],
        ),
    ),
}


__all__ = ["IDE_TOOL_NAMES", "register_ide_tools"]
