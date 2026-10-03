"""Phase 22: SDK session client against scripted local stdio servers."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from omes.tools.mcp_session import mcp_session_call


SERVER_SCRIPT = """\
import json, sys

canned = json.loads(sys.argv[1])

def send(obj):
    sys.stdout.write(json.dumps(obj) + "\\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    method = msg.get("method")
    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion", "2025-06-18")
        send({"jsonrpc": "2.0", "id": msg.get("id"),
              "result": {"protocolVersion": version, "capabilities": {},
                         "serverInfo": {"name": "fake", "version": "0"}}})
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        tools = [{"name": name, "description": "", "inputSchema": {"type": "object"}}
                 for name in canned]
        send({"jsonrpc": "2.0", "id": msg.get("id"), "result": {"tools": tools}})
    elif method == "tools/call":
        params = msg.get("params") or {}
        payload = canned.get(params.get("name"), {"content": [], "isError": True})
        send({"jsonrpc": "2.0", "id": msg.get("id"), "result": payload})
"""

HANG_SCRIPT = """\
import sys, time
Path = __import__("pathlib").Path
Path(sys.argv[1]).write_text(str(__import__("os").getpid()))
time.sleep(30)
"""


def _server(tmp_path: Path, canned: dict) -> list[str]:
    script = tmp_path / "fake_server.py"
    script.write_text(SERVER_SCRIPT, encoding="utf-8")
    return [sys.executable, str(script), json.dumps(canned)]


def test_initialize_and_call_return_canned_blocks(tmp_path: Path):
    command = _server(tmp_path, {"add": {"content": [{"type": "text", "text": "4"}], "isError": False}})
    outcome = mcp_session_call(
        command, "add", {"a": 2, "b": 2}, cwd=str(tmp_path), timeout=10
    )
    assert outcome["result"]["content"] == [{"type": "text", "text": "4"}]
    assert outcome["result"]["is_error"] is False
    assert "error" not in outcome
    json.dumps(outcome)


def test_error_results_carry_error_and_result(tmp_path: Path):
    command = _server(tmp_path, {"missing": {"content": [], "isError": True}})
    outcome = mcp_session_call(command, "missing", {}, cwd=str(tmp_path), timeout=10)
    assert outcome["error"] == "MCP tool reported an error"
    assert outcome["result"]["is_error"] is True


def test_error_results_surface_tool_text(tmp_path: Path):
    command = _server(
        tmp_path, {"bad": {"content": [{"type": "text", "text": "nope"}], "isError": True}}
    )
    outcome = mcp_session_call(command, "bad", {}, cwd=str(tmp_path), timeout=10)
    assert outcome["error"] == "nope"


def test_refusals_spawn_nothing(tmp_path: Path):
    probe = tmp_path / "spawned"
    command = [sys.executable, "-c", f"open({str(probe)!r}, 'w').write('x')"]
    assert mcp_session_call(
        " ".join(command), "t", {}, cwd=str(tmp_path)
    )["error"] == "command must be an argv list, not a string"
    assert "error" in mcp_session_call([], "t", {}, cwd=str(tmp_path))
    assert "error" in mcp_session_call(command, "", {}, cwd=str(tmp_path))
    assert "error" in mcp_session_call(command, "t", [], cwd=str(tmp_path))
    assert "error" in mcp_session_call(command, "t", {}, cwd=str(tmp_path), timeout=0)
    assert "error" in mcp_session_call(
        command, "t", {}, cwd=str(tmp_path / "nope")
    )
    assert not probe.exists()


def test_missing_executable_is_a_spawn_error(tmp_path: Path):
    outcome = mcp_session_call(
        [str(tmp_path / "no-such-server"), "--x"], "t", {}, cwd=str(tmp_path)
    )
    assert "Error" in outcome["error"] or "error" in outcome["error"].lower()
    assert "result" not in outcome


def _dead(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def test_timeout_names_the_timeout_and_reaps_the_child(tmp_path: Path):
    script = tmp_path / "hang.py"
    script.write_text(HANG_SCRIPT, encoding="utf-8")
    pid_file = tmp_path / "hang.pid"
    outcome = mcp_session_call(
        [sys.executable, str(script), str(pid_file)],
        "t",
        {},
        cwd=str(tmp_path),
        timeout=2,
    )
    assert outcome["error"] == "timed out after 2 seconds"
    pid = int(pid_file.read_text(encoding="utf-8"))
    for _ in range(100):
        if _dead(pid):
            break
        time.sleep(0.05)
    assert _dead(pid)
