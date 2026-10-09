# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""The RLM tool surface as a model and registry consumer observes it.

Omitted required fields, a model-supplied ``cwd`` and a misconfigured parent
are driven through ``ToolRegistry.dispatch`` with real human grants, and one
omitted/rejected sequence runs through the real ``OmegaPrimeAgent.run`` with a
``ScriptedModel``. Every file written lands under ``tmp_path``.
"""

from __future__ import annotations

import json

import pytest

from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.rlm import host_for
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.audit.log import AuditLog
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.rlm import RLM_TOOL_NAMES, register_rlm_tools


class _Parent:
    """The host-side parent contract (depth/budget/session wiring)."""

    def __init__(self, session_dir):
        self.delegate_depth = 0
        self.max_depth = 2
        self.max_children = 4
        self.session_dir = str(session_dir)
        self.session_name = None


class _ParentWithoutSessionDir:
    def __init__(self):
        self.delegate_depth = 0
        self.max_depth = 2
        self.max_children = 4
        self.session_name = None


class _RosterStore:
    """A duck-typed session roster that records every row it is asked to create."""

    def __init__(self):
        self.rows = []

    def create(self, *, session_id, name, prompt):
        self.rows.append((session_id, name, prompt))


def _granted(*families, audit=None):
    """A registry whose tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for family in families:
        for name in family:
            receipt = log.approve(name, "phase61-human-reviewer")
            assert receipt["approved"] is True
    return ToolRegistry(approval_log=log, audit=audit)


def _tool_call(name, arguments="{}", call_id="call-1"):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    }


def _run(registry, script, *, max_iterations=10):
    agent = OmegaPrimeAgent(
        ScriptedModel(script),
        registry=registry,
        system_message="SYS",
        max_iterations=max_iterations,
    )
    result = agent.run("go")
    return agent, result


def _model_tool_content(agent, call_id):
    message = next(
        row
        for row in agent.provider_model.seen[-1]
        if row.get("role") == "tool" and row.get("tool_call_id") == call_id
    )
    return message["content"]


def _model_tool_payload(agent, call_id):
    return json.loads(_model_tool_content(agent, call_id))


@pytest.fixture
def rlm_env(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    parent = _Parent(session_dir)
    audit = AuditLog(tmp_path / "audit.ndjson")
    store = _RosterStore()
    registry = _granted(RLM_TOOL_NAMES, audit=audit)
    register_rlm_tools(
        registry,
        parent,
        run_child=lambda prompt, model=None, thinking=None: f"done: {prompt}",
        session_store=store,
    )
    try:
        yield registry, parent, session_dir, audit, store
    finally:
        host_for(parent, True).shutdown()


@pytest.mark.parametrize(
    "tool", ["rlm_spawn", "rlm_delete_subagent", "rlm_rename", "rlm_progress_note"]
)
def test_omitted_required_fields_are_typed_bad_type(rlm_env, tool):
    registry, _parent, _session_dir, _audit, _store = rlm_env

    payload = json.loads(registry.dispatch(tool, {}))

    assert payload["code"] == "bad_type"
    assert json.loads(registry.dispatch("rlm_list_subagents", {})) == []


def test_typed_rejections_are_audited_as_errors(rlm_env):
    registry, _parent, _session_dir, audit, _store = rlm_env

    payload = json.loads(
        registry.dispatch(
            "rlm_spawn", {"prompt": "work", "name": "kid", "schema_version": 99}
        )
    )

    assert payload["code"] == "unsupported_schema_version"
    record = audit.records()[-1]
    assert record["tool"] == "rlm_spawn"
    assert record["verdict"] == "error"
    assert record["reason"].startswith("unsupported_schema_version")
    assert json.loads(registry.dispatch("rlm_list_subagents", {})) == []


def test_create_session_with_cwd_is_typed_error_and_writes_nothing(rlm_env, tmp_path):
    registry, _parent, session_dir, audit, store = rlm_env
    elsewhere = tmp_path / "elsewhere"

    payload = json.loads(
        registry.dispatch(
            "rlm_create_session", {"prompt": "work", "cwd": str(elsewhere)}
        )
    )

    assert payload["error"]
    assert payload["code"] == "unknown_field"
    assert audit.records()[-1]["verdict"] == "error"
    assert store.rows == []
    assert list(session_dir.rglob("*")) == []
    assert not elsewhere.exists()
    assert json.loads(registry.dispatch("rlm_list_subagents", {})) == []


def test_create_session_without_cwd_persists_under_the_parent_directory(rlm_env):
    registry, _parent, session_dir, _audit, store = rlm_env

    created = json.loads(
        registry.dispatch("rlm_create_session", {"prompt": "work", "name": "sess"})
    )

    assert "error" not in created
    assert created["session_file"].startswith(str(session_dir))
    assert [row[1] for row in store.rows] == ["sess"]


def test_blank_names_are_typed_bad_value_and_create_nothing(rlm_env):
    registry, _parent, session_dir, audit, store = rlm_env
    registry.dispatch("rlm_spawn", {"prompt": "real", "name": "kid"})
    collected = json.loads(
        registry.dispatch("rlm_collect", {"targets": ["kid"], "timeout_ms": 5000})
    )
    assert collected[0]["status"] == "done"

    def documents():
        return sorted(path.name for path in session_dir.rglob("*.json"))

    before = documents()
    assert before

    for tool, arguments in (
        ("rlm_spawn", {"prompt": "work", "name": "  "}),
        ("rlm_create_session", {"prompt": "work", "name": "  "}),
        ("rlm_rename", {"target": "kid", "name": "  "}),
    ):
        payload = json.loads(registry.dispatch(tool, arguments))

        assert payload["code"] == "bad_value", tool
        assert audit.records()[-1]["verdict"] == "error", tool

    assert store.rows == []
    assert documents() == before
    listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
    assert [row["session_name"] for row in listed] == ["kid"]


def test_loop_omitted_fields_and_cwd_reach_model_typed_then_recovers(rlm_env, tmp_path):
    registry, _parent, session_dir, _audit, store = rlm_env
    elsewhere = tmp_path / "elsewhere"
    agent, result = _run(
        registry,
        [
            _tool_call("rlm_spawn", "{}", "c-spawn"),
            _tool_call("rlm_rename", "{}", "c-rename"),
            _tool_call(
                "rlm_create_session",
                json.dumps({"prompt": "work", "cwd": str(elsewhere)}),
                "c-cwd",
            ),
            _tool_call("rlm_spawn", '{"prompt":"real","name":"kid"}', "c-good"),
            _tool_call("rlm_collect", '{"targets":["kid"],"timeout_ms":5000}', "c-col"),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    try:
        assert result["final_response"] == "recovered"
        for call_id, code in (
            ("c-spawn", "bad_type"),
            ("c-rename", "bad_type"),
            ("c-cwd", "unknown_field"),
        ):
            content = _model_tool_content(agent, call_id)
            assert content.startswith("error:")
            assert code in content
        assert _model_tool_payload(agent, "c-good")["name"] == "kid"
        collected = _model_tool_payload(agent, "c-col")[0]
        assert collected["status"] == "done"
        assert collected["answer_preview"] == "done: real"
        assert store.rows == []
        assert not elsewhere.exists()
        listed = json.loads(registry.dispatch("rlm_list_subagents", {}))
        assert [row["session_name"] for row in listed] == ["kid"]
        assert list(session_dir.rglob("*"))
    finally:
        agent.close()


def test_register_rejects_parent_without_session_dir_at_registration():
    registry = ToolRegistry()

    with pytest.raises(TypeError, match="session_dir"):
        register_rlm_tools(registry, _ParentWithoutSessionDir())

    assert registry.schemas() == []


def test_register_with_no_parent_registers_every_tool():
    registry = ToolRegistry()

    registered = register_rlm_tools(registry, None)

    assert registered == list(RLM_TOOL_NAMES)
    assert [item["function"]["name"] for item in registry.schemas()] == list(
        RLM_TOOL_NAMES
    )
