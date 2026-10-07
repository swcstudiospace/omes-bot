"""Ultrathink bridge: plan/track/ship flows as Omes registry tools.

Shells to the ultrathink checkout's CLIs (`bin/ultrathink`,
`bin/ultrathink-mcp`, `bin/ultrathink-ship`) behind an injected
runner. No ultrathink source is vendored: this module only execs
the host-installed checkout, which keeps the AGPL boundary at the
process edge. Tests use fakes only.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from omes.tools.registry import ToolRegistry

ULT_TOOL_NAMES = (
    "ult_status",
    "ult_track_complete",
    "ult_session_mark",
    "ult_ship_assess",
    "ult_ship_pr",
    "ult_ship_review",
    "ult_ship_merge",
)

APPROVAL_TOOLS = frozenset({"ult_track_complete", "ult_session_mark", "ult_ship_pr",
                               "ult_ship_review", "ult_ship_merge"})
_MARKS = ("kicked-off", "synced")
OUTPUT_TAIL = 2000


def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}


def _default_run(argv: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        run = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": 127, "stdout": "", "stderr": str(exc)}
    return {"exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}


@dataclass
class UltrathinkContext:
    """Checkout root + command runner. Empty root means unconfigured."""

    root: str | Path = ""
    run: Any = None
    timeout: int = 120


class UltrathinkClient:
    """Ultrathink CLI verbs bound to one context."""

    def __init__(self, ctx: UltrathinkContext) -> None:
        self.ctx = ctx

    def _bin(self, name: str) -> str | None:
        root = str(self.ctx.root or "")
        if not root:
            return None
        return str(Path(root) / "bin" / name)

    def _call(self, binary: str, args: list[str]) -> dict[str, Any]:
        exe = self._bin(binary)
        if exe is None:
            return _error("not_configured", "ultrathink checkout root is not configured")
        run = self.ctx.run if self.ctx.run is not None else _default_run
        result = run([exe, *args], self.ctx.timeout)
        if not isinstance(result, dict):
            return _error("upstream_error", "runner returned no result")
        if result.get("exit_code") != 0:
            tail = str(result.get("stderr") or result.get("stdout") or "")[-OUTPUT_TAIL:]
            return _error("upstream_error", f"{binary} exited {result.get('exit_code')}",
                          output_tail=tail)
        stdout = str(result.get("stdout") or "")
        try:
            return {"ok": True, "result": json.loads(stdout)}
        except ValueError:
            return {"ok": True, "output": stdout[-OUTPUT_TAIL:]}

    def status(self) -> dict[str, Any]:
        """Planner/uplift status from the checkout."""
        return self._call("ultrathink", ["status"])

    def track_complete(self, state: str) -> dict[str, Any]:
        """Finish Linear/Notion rows for one session state file. Approval-gated."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        return self._call("ultrathink-mcp", ["track", "complete", "--state", state])

    def session_mark(self, state: str, mark: str) -> dict[str, Any]:
        """Mark one session kicked-off or synced."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        if mark not in _MARKS:
            raise ValueError("mark must be kicked-off or synced")
        return self._call("ultrathink-mcp", ["session", "mark", "--state", state, mark])

    def ship_assess(self, state: str) -> dict[str, Any]:
        """Assess whether one session is ready to ship."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        return self._call("ultrathink-ship", ["assess", "--state", state])

    def ship_pr(self, state: str) -> dict[str, Any]:
        """Push the branch and open (or reuse) the ship PR. Approval-gated."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        return self._call("ultrathink-ship", ["pr", "--state", state])

    def ship_review(self, state: str) -> dict[str, Any]:
        """Run/resume the Greptile review. Approval-gated."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        return self._call("ultrathink-ship", ["review", "--state", state])

    def ship_merge(self, state: str) -> dict[str, Any]:
        """Merge the reviewed PR when policy allows. Approval-gated."""
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a session state path")
        return self._call("ultrathink-ship", ["merge", "--state", state])


def register_ultrathink_tools(registry: ToolRegistry, client: UltrathinkClient) -> list[str]:
    """Register the 7 ultrathink bridge tools. Writes need approval."""

    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    handlers = {
        "ult_status": lambda: _wrap(client.status),
        "ult_track_complete": lambda state: _wrap(client.track_complete, state),
        "ult_session_mark": lambda state, mark: _wrap(client.session_mark, state, mark),
        "ult_ship_assess": lambda state: _wrap(client.ship_assess, state),
        "ult_ship_pr": lambda state: _wrap(client.ship_pr, state),
        "ult_ship_review": lambda state: _wrap(client.ship_review, state),
        "ult_ship_merge": lambda state: _wrap(client.ship_merge, state),
    }
    if set(handlers) != set(ULT_TOOL_NAMES):
        raise RuntimeError("Ultrathink tool handlers drifted from ULT_TOOL_NAMES")
    for name in ULT_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name],
                          requires_approval=(name in APPROVAL_TOOLS))
    return list(ULT_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_STATE = _string("Session state file path.")
_SCHEMAS: dict[str, tuple[str, dict]] = {
    "ult_status": ("Ultrathink planner status. Read-only.", _object({}, [])),
    "ult_track_complete": ("Finish tracker rows for one session. Requires approval.",
                           _object({"state": _STATE}, ["state"])),
    "ult_session_mark": ("Mark one session kicked-off or synced. Requires approval.",
                         _object({"state": _STATE, "mark": _string("kicked-off or synced.")},
                                ["state", "mark"])),
    "ult_ship_assess": ("Assess ship readiness for one session. Read-only.",
                        _object({"state": _STATE}, ["state"])),
    "ult_ship_pr": ("Push and open (or reuse) the ship PR. Requires approval.",
                    _object({"state": _STATE}, ["state"])),
    "ult_ship_review": ("Run/resume the Greptile review. Requires approval.",
                        _object({"state": _STATE}, ["state"])),
    "ult_ship_merge": ("Merge the reviewed PR when policy allows. Requires approval.",
                       _object({"state": _STATE}, ["state"])),
}


__all__ = ["ULT_TOOL_NAMES", "UltrathinkClient", "UltrathinkContext", "register_ultrathink_tools"]
