"""Phase 36: MCP tool host over the registry."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from omes.mcp_server import (
    SERVER_NAME,
    build_server,
    call_tool_handler,
    default_registry,
    list_tools_handler,
    roster_names,
)
from omes.tools.approvals import ApprovalLog
from omes.tools.coding import register_coding_tools
from omes.tools.infra import InfraClient, InfraContext, register_infra_tools
from omes.tools.registry import ToolRegistry
from omes.tools.ultrathink import (
    UltrathinkClient,
    UltrathinkContext,
    register_ultrathink_tools,
)

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent


def _small_registry(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry(approval_log=ApprovalLog())
    register_coding_tools(registry, tmp_path)
    register_infra_tools(registry, InfraClient(InfraContext()))
    register_ultrathink_tools(registry, UltrathinkClient(UltrathinkContext()))
    return registry


def test_list_tools_matches_registry_and_roster(tmp_path: Path):
    registry = _small_registry(tmp_path)
    assert build_server(registry).name == SERVER_NAME
    listed = asyncio.run(list_tools_handler(registry)(None, None))
    names = [tool.name for tool in listed.tools]
    assert "read_file" in names and "infra_db_health" in names
    assert "ult_status" in names
    schemas = {tool.name: tool.input_schema for tool in listed.tools}
    assert schemas["read_file"]["type"] == "object"

    gated = asyncio.run(list_tools_handler(registry, ["read_file"])(None, None))
    assert [tool.name for tool in gated.tools] == ["read_file"]


def test_call_tool_dispatches_and_marks_errors(tmp_path: Path):
    registry = _small_registry(tmp_path)
    call = call_tool_handler(registry)

    class Params:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    (tmp_path / "note.txt").write_text("hi", encoding="utf-8")
    ok = asyncio.run(call(None, Params("read_file", {"path": "note.txt"})))
    assert ok.is_error in (False, None)
    assert json.loads(ok.content[0].text)["content"] == "hi"

    unknown = asyncio.run(call(None, Params("nope", {})))
    assert unknown.is_error is True
    assert "Unknown tool" in unknown.content[0].text

    gated = asyncio.run(call(
        None, Params("infra_railway_redeploy",
                     {"project": "a", "service": "b", "prior_deployment_id": "d"})))
    assert gated.is_error is True
    assert "approval required" in gated.content[0].text


def test_default_registry_serves_the_roster(tmp_path: Path):
    roster = roster_names((OMES / "contracts" / "tool-rosters" / "omes.yaml").read_text(
        encoding="utf-8"))
    registry = default_registry(ROOT, tmp_path)
    listed = asyncio.run(list_tools_handler(registry, roster)(None, None))
    served = [tool.name for tool in listed.tools]
    assert served == [name for name in roster if name != "delegate_task"]
    assert "delegate_task" not in served


def test_stdio_roundtrip_through_own_client(tmp_path: Path):
    from omes.tools.mcp_session import mcp_session_call

    command = [sys.executable, "-m", "omes.mcp_server", "--root", str(ROOT),
               "--home", str(tmp_path)]
    called = mcp_session_call(command, "infra_db_health", {}, cwd=str(ROOT), timeout=30)
    assert "error" not in called, called
    text = called["result"]["content"][0]["text"]
    assert json.loads(text)["summary"] == {}
