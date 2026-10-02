"""Local terminal: an argv list, a working directory inside the root, and a timeout.

Adapted from the local backend of Hermes ``tools/terminal_tool.py``. There is no
shell string, and no Docker, SSH, or other backend. ``shell=True`` is never used.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from omes.tools.file_ops import PathError, require_directory, resolve_inside

DEFAULT_TIMEOUT_SECONDS = 30


def run_terminal(
    root: str | Path,
    argv: list[str],
    cwd: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Exec ``argv`` with ``cwd`` inside ``root``. Capture stdout, stderr, and the exit code.

    A string ``argv`` is refused. It is not passed to a shell. A working directory
    outside the root is refused before the process is started.
    """
    if isinstance(argv, str):
        return {"error": "argv must be a list of arguments, not a shell string"}
    if not isinstance(argv, list) or not argv or any(not isinstance(part, str) for part in argv):
        return {"error": "argv must be a non-empty list of strings"}
    if argv[0] == "":
        return {"error": "argv[0] must be the program to run"}
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        return {"error": "timeout must be a positive number of seconds"}
    try:
        base = require_directory(root)
        workdir = resolve_inside(base, "." if cwd is None else cwd)
    except PathError as exc:
        return {"error": str(exc)}
    if not workdir.is_dir():
        return {"error": f"working directory is not a directory: {cwd}"}
    try:
        completed = subprocess.run(
            argv,
            cwd=str(workdir),
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "error": f"timed out after {timeout} seconds",
            "stdout": _text(exc.stdout),
            "stderr": _text(exc.stderr),
            "exit_code": None,
        }
    except OSError as exc:
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "stdout": "",
            "stderr": "",
            "exit_code": 127,
        }
    return {
        "stdout": _text(completed.stdout),
        "stderr": _text(completed.stderr),
        "exit_code": completed.returncode,
    }


def _text(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    return data.decode("utf-8", errors="replace")


__all__ = ["DEFAULT_TIMEOUT_SECONDS", "run_terminal"]
