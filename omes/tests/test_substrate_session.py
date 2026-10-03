"""Phase 41: substrate session, loop wiring, docs_search tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.model import ScriptedModel
from omes.substrate.client import SubstrateError
from omes.substrate.session import SubstrateSession
from omes.tools.approvals import ApprovalLog
from omes.tools.registry import ToolRegistry
from omes.tools.substrate_tools import SUBSTRATE_TOOL_NAMES, register_substrate_tools


class _FakeClient:
    """Scripted brief/emit/docs_search; every call recorded."""

    def __init__(
        self,
        brief: str = "# brief\n",
        docs: dict | None = None,
        emit_error: Exception | None = None,
        brief_error: Exception | None = None,
    ) -> None:
        self._brief = brief
        self._docs = docs if docs is not None else {"ok": True, "status": 200, "body": {}}
        self._emit_error = emit_error
        self._brief_error = brief_error
        self.briefs: list[dict] = []
        self.emits: list[dict] = []
        self.docs_calls: list[str] = []

    def brief(self, repo=None, branch=None, graph_id=None) -> str:
        self.briefs.append({"repo": repo, "branch": branch, "graph_id": graph_id})
        if self._brief_error is not None:
            raise self._brief_error
        return self._brief

    def emit(self, kind: str, summary: str, **fields) -> dict:
        self.emits.append({"kind": kind, "summary": summary, **fields})
        if self._emit_error is not None:
            raise self._emit_error
        return {"stored": True, "id": "e1"}

    def docs_search(self, query: str) -> dict:
        self.docs_calls.append(query)
        if isinstance(self._docs, Exception):
            raise self._docs
        return self._docs

    def graph_claim(self, graph_id: str, node_id: str, session_id: str, ttl: int = 3600) -> dict:
        self.emits.append({"kind": "claim", "graph_id": graph_id, "node_id": node_id})
        return {"ok": True, "token": "lease-tok", "expires": "soon"}

    def graph_release(self, graph_id: str, node_id: str) -> str:
        return f"Released {graph_id}/{node_id}."

    def graph_complete(self, graph_id: str, node_id: str) -> str:
        return f"Completed {graph_id}/{node_id}."

    def graph_heartbeat(self, graph_id: str, node_id: str, token: str) -> dict:
        return {"ok": True, "graph_id": graph_id, "node_id": node_id}


def _session(client: _FakeClient, tmp_path: Path | None = None, **kwargs) -> SubstrateSession:
    if tmp_path is not None and "brief_dir" not in kwargs:
        kwargs["brief_dir"] = tmp_path
    return SubstrateSession(client, session_id="s1", graph_id="ut-1", **kwargs)


def test_open_emits_start_caches_and_writes_brief(tmp_path: Path) -> None:
    client = _FakeClient()
    session = _session(client, tmp_path)
    assert session.open() == "# brief\n"
    assert session.open() == "# brief\n"
    assert len(client.briefs) == 1
    assert client.emits[0]["kind"] == "session.start"
    assert client.emits[0]["session_id"] == "s1"
    assert client.emits[0]["graph_id"] == "ut-1"
    assert session.brief_block() == "## Substrate brief\n# brief\n"
    assert (tmp_path / ".substrate" / "BRIEF.md").read_text() == "# brief\n"


def test_open_empty_brief_writes_no_file(tmp_path: Path) -> None:
    client = _FakeClient(brief="")
    session = _session(client, tmp_path)
    assert session.open() == ""
    assert session.brief_block() == ""
    assert not (tmp_path / ".substrate" / "BRIEF.md").exists()


def test_open_never_raises(tmp_path: Path) -> None:
    client = _FakeClient(brief_error=RuntimeError("down"))
    session = _session(client, tmp_path)
    assert session.open() == ""
    assert session.brief_block() == ""


def test_prompt_tool_file_turn_close_events() -> None:
    client = _FakeClient()
    session = _session(client)
    session.open()
    session.on_prompt("do the thing " + "x" * 500)
    session.on_tool_call("read_file", {"path": "a.py"}, ok=True)
    session.on_tool_call("write_file", {"path": "b.py", "content": "secret"}, ok=False)
    session.on_turn_end("stop")
    session.close()
    session.close()
    kinds = [event["kind"] for event in client.emits]
    assert kinds == [
        "session.start",
        "prompt",
        "tool.call",
        "tool.call",
        "file.edit",
        "note",
        "session.end",
    ]
    prompt = client.emits[1]
    assert len(prompt["summary"]) == 240
    assert all(event["session_id"] == "s1" for event in client.emits)
    assert client.emits[3]["summary"] == "write_file error"
    assert client.emits[4]["summary"] == "write_file b.py"
    assert "secret" not in json.dumps(client.emits)
    assert client.emits[5]["summary"] == "turn ended: stop"


def test_hooks_never_raise() -> None:
    client = _FakeClient(emit_error=RuntimeError("down"))
    session = _session(client)
    session.open()
    session.on_prompt("hi")
    session.on_tool_call("x", None)
    session.on_turn_end(None)
    session.close()


def _tool_call(name: str, arguments: str = "{}", call_id: str = "call-1") -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}
        ],
    }


def test_loop_injects_brief_and_reports_trail(tmp_path: Path) -> None:
    client = _FakeClient()
    session = _session(client, tmp_path, repo="o/n")
    model = ScriptedModel(
        [
            _tool_call("read_file", '{"path": "a.py"}'),
            {"role": "assistant", "content": "done"},
        ]
    )
    agent = Agent(
        model=model,
        tools={"read_file": lambda path: "contents"},
        substrate=session,
    )
    result = run_conversation(agent, "read a.py", system_message="Be brief.")
    assert result["turn_exit_reason"] == "text_response(finish_reason=stop)"
    system_row = model.seen[0][0]
    assert system_row["role"] == "system"
    assert "## Substrate brief\n# brief\n" in system_row["content"]
    assert "Be brief." in system_row["content"]
    kinds = [event["kind"] for event in client.emits]
    assert kinds == ["session.start", "prompt", "tool.call", "note"]
    assert client.emits[2]["summary"] == "read_file ok"
    assert client.emits[1]["repo"] == "o/n"


def test_loop_without_substrate_is_unchanged() -> None:
    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(model=model)
    result = run_conversation(agent, "hi", system_message="Be brief.")
    assert result["turn_exit_reason"] == "text_response(finish_reason=stop)"
    assert "Be brief." in model.seen[0][0]["content"]


def _registry(client: _FakeClient) -> ToolRegistry:
    registry = ToolRegistry()
    assert register_substrate_tools(registry, client) == list(SUBSTRATE_TOOL_NAMES)
    return registry


def test_docs_tool_retrieval_passthrough() -> None:
    body = {"code": 0, "data": {"chunks": [{"content": "cited"}]}}
    registry = _registry(_FakeClient(docs={"ok": True, "status": 200, "body": body}))
    assert json.loads(registry.dispatch("substrate_docs_search", {"query": "q"})) == {
        "retrieval": body
    }


def test_docs_tool_plane_and_transport_errors() -> None:
    registry = _registry(_FakeClient(docs={"ok": False, "error": "RAGFLOW_URL missing"}))
    assert "RAGFLOW_URL" in json.loads(registry.dispatch("substrate_docs_search", {"query": "q"}))["error"]
    down = _registry(_FakeClient(docs=SubstrateError("down")))
    assert "unreachable" in json.loads(down.dispatch("substrate_docs_search", {"query": "q"}))["error"]
    assert "error" in json.loads(registry.dispatch("substrate_docs_search", {"query": ""}))


def _approved_registry(client: _FakeClient) -> ToolRegistry:
    log = ApprovalLog()
    for name in (
        "substrate_graph_claim",
        "substrate_graph_release",
        "substrate_graph_complete",
    ):
        assert log.approve(name, "person")["approved"] is True
    registry = ToolRegistry(approval_log=log)
    assert register_substrate_tools(registry, client) == list(SUBSTRATE_TOOL_NAMES)
    return registry


def test_graph_tools_dispatch_with_lease() -> None:
    registry = _approved_registry(_FakeClient())
    claim = json.loads(
        registry.dispatch(
            "substrate_graph_claim",
            {"graph_id": "g", "node_id": "n", "session_id": "s1"},
        )
    )
    assert claim == {"ok": True, "token": "lease-tok", "expires": "soon"}
    release = json.loads(
        registry.dispatch("substrate_graph_release", {"graph_id": "g", "node_id": "n"})
    )
    assert release == {"result": "Released g/n."}
    complete = json.loads(
        registry.dispatch("substrate_graph_complete", {"graph_id": "g", "node_id": "n"})
    )
    assert complete == {"result": "Completed g/n."}
    beat = json.loads(
        registry.dispatch(
            "substrate_graph_heartbeat",
            {"graph_id": "g", "node_id": "n", "token": "lease-tok"},
        )
    )
    assert beat == {"ok": True, "graph_id": "g", "node_id": "n"}
    bad = json.loads(
        registry.dispatch("substrate_graph_claim", {"graph_id": "", "node_id": "n", "session_id": "s"})
    )
    assert "graph_id" in bad["error"]


def test_graph_mutations_require_approval() -> None:
    registry = ToolRegistry(approval_log=ApprovalLog())
    register_substrate_tools(registry, _FakeClient())
    for name in (
        "substrate_graph_claim",
        "substrate_graph_release",
        "substrate_graph_complete",
    ):
        denied = json.loads(registry.dispatch(name, {"graph_id": "g", "node_id": "n"}))
        assert denied["error"] == "approval required"
    heartbeat = json.loads(
        registry.dispatch(
            "substrate_graph_heartbeat",
            {"graph_id": "g", "node_id": "n", "token": "t"},
        )
    )
    assert heartbeat["ok"] is True
