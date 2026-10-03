"""Phase 9: an LSP diagnostic and a DAP breakpoint stop, via fixture servers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from omes.tools.ide import IDE_TOOL_NAMES, register_ide_tools
from omes.tools.offer import offered_schemas
from omes.tools.registry import ToolRegistry

OMES = Path(__file__).resolve().parents[1]
ROSTER = OMES / "contracts" / "tool-rosters" / "omes.yaml"

_LSP_FIXTURE = '''\
import json
import sys

out = sys.stdout.buffer
inp = sys.stdin.buffer


def read_message():
    headers = b""
    while b"\\r\\n\\r\\n" not in headers:
        chunk = inp.read(1)
        if not chunk:
            return None
        headers += chunk
    head, rest = headers.split(b"\\r\\n\\r\\n", 1)
    length = 0
    for line in head.split(b"\\r\\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    body = rest
    while len(body) < length:
        more = inp.read(length - len(body))
        if not more:
            return None
        body += more
    return json.loads(body.decode("utf-8"))


def send(message):
    body = json.dumps(message).encode("utf-8")
    out.write(b"Content-Length: %d\\r\\n\\r\\n" % len(body) + body)
    out.flush()


while True:
    message = read_message()
    if message is None:
        break
    method = message.get("method")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": {}}})
    elif method == "textDocument/didOpen":
        doc = message["params"]["textDocument"]
        send(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": doc["uri"],
                    "diagnostics": [
                        {
                            "range": {
                                "start": {"line": 1, "character": 0},
                                "end": {"line": 1, "character": 9},
                            },
                            "severity": 1,
                            "message": "fixture: undefined name 'karel'",
                        }
                    ],
                },
            }
        )
    elif method == "shutdown":
        send({"jsonrpc": "2.0", "id": message["id"], "result": None})
    elif method == "exit":
        break
'''

_DAP_FIXTURE = '''\
import json
import sys

out = sys.stdout.buffer
inp = sys.stdin.buffer
seq = 0
break_lines = [1]


def read_message():
    headers = b""
    while b"\\r\\n\\r\\n" not in headers:
        chunk = inp.read(1)
        if not chunk:
            return None
        headers += chunk
    head, rest = headers.split(b"\\r\\n\\r\\n", 1)
    length = 0
    for line in head.split(b"\\r\\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    body = rest
    while len(body) < length:
        more = inp.read(length - len(body))
        if not more:
            return None
        body += more
    return json.loads(body.decode("utf-8"))


def send(message):
    global seq
    seq += 1
    message["seq"] = seq
    body = json.dumps(message).encode("utf-8")
    out.write(b"Content-Length: %d\\r\\n\\r\\n" % len(body) + body)
    out.flush()


def respond(request, body=None):
    send(
        {
            "type": "response",
            "request_seq": request["seq"],
            "command": request["command"],
            "success": True,
            "body": body or {},
        }
    )


while True:
    message = read_message()
    if message is None:
        break
    command = message.get("command")
    if command == "initialize":
        respond(message, {"supportsConfigurationDoneRequest": True})
        send({"type": "event", "event": "initialized"})
    elif command == "launch":
        respond(message)
    elif command == "setBreakpoints":
        wanted = message["arguments"]["breakpoints"]
        break_lines[:] = [entry["line"] for entry in wanted] or [1]
        respond(
            message,
            {"breakpoints": [{"verified": True, "line": line} for line in break_lines]},
        )
    elif command == "configurationDone":
        respond(message)
        send(
            {
                "type": "event",
                "event": "stopped",
                "body": {"reason": "breakpoint", "threadId": 1},
            }
        )
    elif command == "threads":
        respond(message, {"threads": [{"id": 1, "name": "main"}]})
    elif command == "stackTrace":
        respond(
            message,
            {
                "stackFrames": [
                    {"id": 1, "name": "main", "line": break_lines[0], "column": 1}
                ]
            },
        )
    elif command == "disconnect":
        respond(message)
        break
'''


def _load(payload: str) -> dict:
    return json.loads(payload)


def _registry(root: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_ide_tools(registry, root)
    return registry


def _fixture_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "lsp_server.py").write_text(_LSP_FIXTURE, encoding="utf-8")
    (root / "dap_adapter.py").write_text(_DAP_FIXTURE, encoding="utf-8")
    (root / "broken.py").write_text("value = 1\nprint(karel)\n", encoding="utf-8")
    (root / "app.py").write_text("a = 1\nb = 2\nc = a + b\n", encoding="utf-8")
    return root


def test_lsp_session_returns_a_diagnostic_for_the_known_error(tmp_path: Path):
    root = _fixture_project(tmp_path)
    registry = _registry(root)
    command = [sys.executable, str(root / "lsp_server.py")]

    found = _load(
        registry.dispatch(
            "lsp_diagnostics", {"command": command, "path": "broken.py"}
        )
    )

    assert "error" not in found
    assert found["path"] == "broken.py"
    assert len(found["diagnostics"]) >= 1
    diagnostic = found["diagnostics"][0]
    assert diagnostic["severity"] == 1
    assert "karel" in diagnostic["message"]
    assert diagnostic["range"]["start"]["line"] == 1


def test_lsp_string_command_starts_nothing(tmp_path: Path):
    root = _fixture_project(tmp_path)
    registry = _registry(root)

    refused = _load(
        registry.dispatch(
            "lsp_diagnostics",
            {"command": "/nonexistent/lsp-server-xyz", "path": "broken.py"},
        )
    )

    assert refused["error"] == "command must be an argv list, not a string"


def test_dap_session_stops_on_the_breakpoint(tmp_path: Path):
    root = _fixture_project(tmp_path)
    registry = _registry(root)
    command = [sys.executable, str(root / "dap_adapter.py")]

    stopped = _load(
        registry.dispatch("dap_stop", {"command": command, "path": "app.py", "line": 3})
    )

    assert "error" not in stopped
    assert stopped["stopped"] is True
    assert stopped["reason"] == "breakpoint"
    assert stopped["thread_id"] == 1
    assert {"name": "main", "line": 3} in stopped["frames"]
    assert stopped["breakpoints"] == [{"verified": True, "line": 3}]


def test_dap_bad_line_starts_nothing(tmp_path: Path):
    root = _fixture_project(tmp_path)
    registry = _registry(root)
    command = [sys.executable, str(root / "dap_adapter.py")]

    refused = _load(
        registry.dispatch("dap_stop", {"command": command, "path": "app.py", "line": 0})
    )

    assert refused["error"] == "line must be a positive integer"


def test_roster_offers_both_ide_names(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    roster = _roster_names(ROSTER.read_text(encoding="utf-8"))
    offered = offered_schemas(registry, roster)
    names = [item["function"]["name"] for item in offered]

    assert list(IDE_TOOL_NAMES) == ["lsp_diagnostics", "dap_stop"]
    for name in IDE_TOOL_NAMES:
        assert name in names


def _roster_names(text: str) -> list[str]:
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
        if line.strip() and not line.startswith("#") and not line.startswith(" "):
            break
    return names
