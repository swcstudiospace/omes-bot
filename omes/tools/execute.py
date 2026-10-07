"""Run one Python script in a short-lived local process.

Adapted from Hermes ``tools/code_execution_tool.py``. There is no persistent
kernel and no remote sandbox. Empty code does not start a process. On timeout
the child is killed.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


def execute_code(code: str, *, home: str | Path, timeout: float = 5) -> dict[str, Any]:
    """Write ``code`` under ``home`` and run it with ``sys.executable``.

    ``cwd`` is ``home``. ``shell`` is never true. Empty or whitespace-only code
    returns an error and writes nothing. A timeout returns an error and a
    non-zero exit code.
    """
    if not isinstance(code, str) or code.strip() == "":
        return {"error": "code must be non-empty Python source"}
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
    ):
        return {"error": "timeout must be a positive number of seconds"}
    root = Path(home)
    if not root.is_dir():
        return {"error": f"home is not a directory: {home}"}
    script_dir = root / ".omes-exec"
    try:
        script_dir.mkdir(exist_ok=True)
        script = script_dir / f"{uuid.uuid4().hex}.py"
        script.write_text(code, encoding="utf-8")
    except OSError as exc:
        return {"error": f"could not write the script: {exc}"}
    return _run([sys.executable, str(script)], cwd=root, timeout=timeout)


def _run(argv: list[str], *, cwd: Path, timeout: float) -> dict[str, Any]:
    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
    except OSError as exc:
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "stdout": "",
            "stderr": "",
            "exit_code": 127,
        }
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stdout, stderr, code = _kill(proc)
        return {
            "error": f"timed out after {timeout} seconds",
            "stdout": _text(stdout),
            "stderr": _text(stderr),
            "exit_code": code,
        }
    return {
        "stdout": _text(stdout),
        "stderr": _text(stderr),
        "exit_code": proc.returncode,
    }


def _kill(proc: subprocess.Popen[bytes]) -> tuple[bytes, bytes, int]:
    """SIGKILL the child's process group, then reap it. The exit is non-zero."""
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            with contextlib.suppress(OSError):
                proc.kill()
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            proc.kill()
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


__all__ = ["execute_code"]
