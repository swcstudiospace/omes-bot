"""Phase 6: local platform tools, the approval gate, and plugin registration."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import pytest

from omes.tools.approvals import ApprovalLog
from omes.tools.browser import BrowserSession
from omes.tools.offer import offered_schemas
from omes.tools.platform import PLATFORM_TOOL_NAMES, register_platform_tools
from omes.tools.plugins import load_plugins
from omes.tools.registry import ToolRegistry

OMES = Path(__file__).resolve().parents[1]
ROSTER = OMES / "contracts" / "tool-rosters" / "omes.yaml"

_SCHEMA = {"type": "object", "properties": {}, "required": []}


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


def _load(raw: str) -> dict:
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    return parsed


def _files(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


class _Page:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.page = "<page>example</page>"

    def navigate(self, url: str) -> str:
        self.urls.append(url)
        return self.page

    def snapshot(self) -> str:
        return self.page


def test_execute_code_runs_python_and_refuses_empty_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    registry = ToolRegistry()
    assert register_platform_tools(registry, home=home) == list(PLATFORM_TOOL_NAMES)

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("empty code started a process")

    with monkeypatch.context() as patch:
        patch.setattr("omes.tools.execute.subprocess.Popen", fail_popen)
        empty = _load(registry.dispatch("execute_code", {"code": "  \n\t"}))
    assert "error" in empty
    assert _files(home) == []

    ran = _load(registry.dispatch("execute_code", {"code": "print(1)"}))
    assert ran["stdout"].strip() == "1"
    assert ran["exit_code"] == 0
    where = _load(registry.dispatch("execute_code", {"code": "import os; print(os.getcwd())"}))
    assert where["exit_code"] == 0
    assert Path(where["stdout"].strip()).resolve() == home.resolve()
    failed = _load(registry.dispatch("execute_code", {"code": "import sys; sys.exit(3)"}))
    assert failed["exit_code"] == 3
    assert "error" not in failed

    pid_path = home / "sleep.pid"
    timed = _load(
        registry.dispatch(
            "execute_code",
            {
                "code": (
                    "import os, time\n"
                    f"open({str(pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))\n"
                    "time.sleep(30)\n"
                ),
                "timeout": 1,
            },
        )
    )
    assert "error" in timed
    assert timed["exit_code"] != 0
    assert "stdout" in timed and "stderr" in timed
    pid = int(pid_path.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_mcp_call_reads_one_json_line_and_refuses_a_string_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    home = tmp_path / "home"
    home.mkdir()
    fixture = home / "mcp_echo.py"
    fixture.write_text(
        "import json\n"
        "import sys\n"
        "request = json.loads(sys.stdin.readline())\n"
        "params = request.get('params') or {}\n"
        "ok = (\n"
        "    request.get('jsonrpc') == '2.0'\n"
        "    and request.get('method') == 'tools/call'\n"
        "    and params.get('name') == 'echo'\n"
        "    and params.get('arguments') == {'text': 'ping'}\n"
        ")\n"
        "if not ok:\n"
        "    sys.stderr.write('bad request\\n')\n"
        "    sys.exit(2)\n"
        "sys.stdout.write('{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"text\":\"ping\"}}\\n')\n",
        encoding="utf-8",
    )
    registry = ToolRegistry()
    register_platform_tools(registry, home=home)

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("string command started a process")

    with monkeypatch.context() as patch:
        patch.setattr("omes.tools.mcp_client.subprocess.Popen", fail_popen)
        refused = _load(
            registry.dispatch(
                "mcp_call",
                {"command": sys.executable, "tool": "echo", "arguments": {"text": "ping"}},
            )
        )
    assert "error" in refused

    called = _load(
        registry.dispatch(
            "mcp_call",
            {
                "command": [sys.executable, str(fixture)],
                "tool": "echo",
                "arguments": {"text": "ping"},
            },
        )
    )
    assert called == {"result": {"text": "ping"}}

    sleeper = home / "sleep_mcp.py"
    sleeper.write_text(
        "import os\n"
        "import time\n"
        "from pathlib import Path\n"
        "Path('mcp.pid').write_text(str(os.getpid()), encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    timed = _load(
        registry.dispatch(
            "mcp_call",
            {
                "command": [sys.executable, str(sleeper)],
                "tool": "echo",
                "arguments": {},
                "timeout": 1,
            },
        )
    )
    assert "error" in timed
    assert timed["exit_code"] != 0
    assert "stdout" in timed and "stderr" in timed
    pid = int((home / "mcp.pid").read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_browser_navigate_and_snapshot_use_the_injected_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def refuse_socket(*_args, **_kwargs):
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "socket", refuse_socket)
    page = _Page()
    registry = ToolRegistry()
    register_platform_tools(registry, home=tmp_path, browser=BrowserSession(page))
    navigated = _load(registry.dispatch("browser_navigate", {"url": "https://example.test/omes"}))
    assert navigated == {"url": "https://example.test/omes", "page": page.page}
    assert page.urls == ["https://example.test/omes"]
    assert _load(registry.dispatch("browser_snapshot", {})) == {"page": page.page}

    closed = ToolRegistry()
    register_platform_tools(closed, home=tmp_path, browser=None)
    assert "error" in _load(closed.dispatch("browser_navigate", {"url": "https://example.test"}))
    assert "error" in _load(closed.dispatch("browser_snapshot", {}))
    assert page.urls == ["https://example.test/omes"]
    missing = BrowserSession(None)
    assert "error" in missing.browser_navigate("https://example.test")
    assert "error" in missing.browser_snapshot()


def test_approval_gate_blocks_until_a_person_approves():
    calls: list[str] = []

    def handler() -> dict:
        calls.append("ran")
        return {"ok": True}

    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log)
    registry.register("danger", "Needs a person.", _SCHEMA, handler, requires_approval=True)
    blocked = _load(registry.dispatch("danger", {}))
    assert blocked == {"error": "approval required", "tool": "danger"}
    assert calls == []
    refused = log.approve("danger", "bot-00-omes")
    assert refused["approved"] is False
    assert log.is_approved("danger") is False
    still = _load(registry.dispatch("danger", {}))
    assert still == {"error": "approval required", "tool": "danger"}
    assert calls == []
    accepted = log.approve("danger", "person")
    assert accepted["approved"] is True
    assert log.is_approved("danger") is True
    assert _load(registry.dispatch("danger", {})) == {"ok": True}
    assert calls == ["ran"]

    bare_calls: list[str] = []

    def bare_handler() -> dict:
        bare_calls.append("ran")
        return {"ok": True}

    bare = ToolRegistry()
    bare.register("danger", "Needs a person.", _SCHEMA, bare_handler, requires_approval=True)
    assert _load(bare.dispatch("danger", {})) == {"error": "approval required", "tool": "danger"}
    assert bare_calls == []


def test_load_plugins_registers_echo_and_skips_a_symlink_outside_home(tmp_path: Path):
    home = tmp_path / "home"
    echo = home / "plugins" / "echo"
    echo.mkdir(parents=True)
    (echo / "plugin.py").write_text(
        "def register(registry):\n"
        "    def plugin_echo():\n"
        "        return {'payload': 'echo'}\n"
        "    registry.register(\n"
        "        'plugin_echo',\n"
        "        'Return a fixed payload.',\n"
        "        {'type': 'object', 'properties': {}, 'required': []},\n"
        "        plugin_echo,\n"
        "    )\n",
        encoding="utf-8",
    )
    bare = home / "plugins" / "bare"
    bare.mkdir()
    (bare / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")

    outside = tmp_path / "outside" / "leave"
    outside.mkdir(parents=True)
    marker = tmp_path / "outside" / "loaded.txt"
    (outside / "plugin.py").write_text(
        "def register(registry):\n"
        "    from pathlib import Path\n"
        f"    Path({str(marker)!r}).write_text('yes', encoding='utf-8')\n"
        "    registry.register(\n"
        "        'plugin_leave',\n"
        "        'Should not load.',\n"
        "        {'type': 'object', 'properties': {}, 'required': []},\n"
        "        lambda: {'payload': 'nope'},\n"
        "    )\n",
        encoding="utf-8",
    )
    (home / "plugins" / "leave").symlink_to(outside, target_is_directory=True)

    registry = ToolRegistry()
    loaded = load_plugins(home, registry)
    assert loaded == ["plugin_echo"]
    assert _load(registry.dispatch("plugin_echo", {})) == {"payload": "echo"}
    names = [item["function"]["name"] for item in registry.schemas()]
    assert "plugin_leave" not in names
    assert marker.exists() is False

    boom_home = tmp_path / "boom"
    boom = boom_home / "plugins" / "boom"
    boom.mkdir(parents=True)
    (boom / "plugin.py").write_text(
        "def register(registry):\n    raise RuntimeError('plugin failed')\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="plugin failed"):
        load_plugins(boom_home, ToolRegistry())


def test_offered_schemas_include_platform_names_and_omit_an_extra_tool(tmp_path: Path):
    registry = ToolRegistry()
    registered = register_platform_tools(registry, home=tmp_path)
    assert registered == list(PLATFORM_TOOL_NAMES)
    registry.register("not_on_roster", "Registered but not offered.", _SCHEMA, lambda: {"ok": True})
    roster = _roster_names(ROSTER.read_text(encoding="utf-8"))
    assert roster[-len(PLATFORM_TOOL_NAMES) :] == list(PLATFORM_TOOL_NAMES)
    offered = offered_schemas(registry, roster)
    names = [item["function"]["name"] for item in offered]
    assert names == list(PLATFORM_TOOL_NAMES)
    for platform_name in PLATFORM_TOOL_NAMES:
        assert platform_name in names
    assert "not_on_roster" not in names
    assert _load(registry.dispatch("not_on_roster", {})) == {"ok": True}
