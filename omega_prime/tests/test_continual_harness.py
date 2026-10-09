"""Tests for the continual-harness port (Phase 56).

Hermetic: tmp_path stores, no network. Behavior contract:
prime-agent-runtime/src/rlm/harness.py + pa-core/src/refinement/ @ 967eb13f.
"""

from __future__ import annotations

import json
import os

import pytest

from omega_prime.agent.refine import refine
from omega_prime.learning.harness import KINDS, HarnessState
from omega_prime.tools.harness import HARNESS_TOOL_NAMES, register_harness_tools
from omega_prime.tools.registry import ToolRegistry


def _state(tmp_path, scope="local"):
    return HarnessState(tmp_path / scope, scope=scope).load()


# --- state store CRUD + validation -------------------------------------------


def test_upsert_and_get_roundtrip(tmp_path):
    state = _state(tmp_path)
    entry = state.upsert("prompt", "p1", title="Note", body="remember this")
    assert entry.kind == "prompt" and entry.id == "p1"
    assert state.get("prompt", "p1").body == "remember this"


def test_upsert_updates_and_preserves_created_at(tmp_path):
    state = _state(tmp_path)
    first = state.upsert("memory", "m1", title="T", body="v1")
    second = state.upsert("memory", "m1", title="T", body="v2")
    assert second.created_at == first.created_at
    assert state.get("memory", "m1").body == "v2"


def test_all_five_kinds_accepted(tmp_path):
    state = _state(tmp_path)
    for kind in KINDS:
        state.upsert(kind, f"{kind}-1", title="t", body="b")
    assert len(state.list_entries()) == 5


def test_unknown_kind_rejected(tmp_path):
    state = _state(tmp_path)
    with pytest.raises(ValueError, match="unknown harness kind"):
        state.upsert("bogus", "x", title="t", body="b")


def test_entry_shape_validation(tmp_path):
    state = _state(tmp_path)
    with pytest.raises(ValueError, match="requires a non-empty id"):
        state.upsert("prompt", "", title="t", body="b")
    with pytest.raises(ValueError, match="requires a title"):
        state.upsert("prompt", "p", title="", body="b")


def test_list_by_kind_and_delete(tmp_path):
    state = _state(tmp_path)
    state.upsert("skill", "s1", title="t", body="b")
    state.upsert("memory", "m1", title="t", body="b")
    assert [e.id for e in state.list_entries("skill")] == ["s1"]
    assert state.delete("skill", "s1") is True
    assert state.get("skill", "s1") is None
    assert state.delete("skill", "s1") is False


def test_persistence_roundtrip(tmp_path):
    state = _state(tmp_path)
    state.upsert("prompt", "p1", title="Note", body="body")
    state.save()
    reloaded = _state(tmp_path)
    assert reloaded.get("prompt", "p1").body == "body"


def test_local_and_global_scopes_are_separate(tmp_path):
    local = _state(tmp_path, "local")
    global_ = _state(tmp_path, "global")
    local.upsert("prompt", "p1", title="t", body="local")
    local.save()
    global_.upsert("prompt", "p1", title="t", body="global")
    global_.save()
    assert _state(tmp_path, "local").get("prompt", "p1").body == "local"
    assert _state(tmp_path, "global").get("prompt", "p1").body == "global"


def test_save_refuses_to_clobber_changed_file(tmp_path):
    state = _state(tmp_path)
    state.upsert("prompt", "p1", title="t", body="b")
    state.save()
    # Simulate a concurrent writer, forcing a distinct mtime.
    state.path.write_text(state.path.read_text() + " ", encoding="utf-8")
    bumped = state.path.stat().st_mtime + 10
    os.utime(state.path, (bumped, bumped))
    state.upsert("prompt", "p2", title="t", body="b")
    with pytest.raises(RuntimeError, match="refusing to clobber"):
        state.save()


# --- refinement + rollback -----------------------------------------------------


def test_refinement_requires_evidence(tmp_path):
    state = _state(tmp_path)
    with pytest.raises(ValueError, match="non-empty evidence"):
        state.record_refinement(trigger="t", changes={}, evidence=[], outcome="o")


def test_refinement_snapshots_and_rollback_restores(tmp_path):
    state = _state(tmp_path)
    state.upsert("prompt", "p1", title="t", body="before")
    state.record_refinement(
        trigger="review",
        changes={"applied": ["p1"]},
        evidence=["saw it"],
        outcome="applied 1",
    )
    state.upsert("prompt", "p1", title="t", body="after")
    assert state.get("prompt", "p1").body == "after"
    assert state.rollback() is True
    assert state.get("prompt", "p1").body == "before"


def test_rollback_without_snapshot_is_false(tmp_path):
    assert _state(tmp_path).rollback() is False


# --- refine pass -----------------------------------------------------------------


def test_refine_applies_only_evidence_backed(tmp_path):
    state = _state(tmp_path)
    trajectory = [{"role": "tool", "content": "the deploy failed with OOM"}]
    result = refine(
        state,
        trigger="review",
        trajectory=trajectory,
        proposals=[
            {
                "kind": "memory",
                "id": "m1",
                "title": "OOM",
                "body": "deploy OOMs",
                "evidence": ["the deploy failed with OOM"],
            },
            {
                "kind": "memory",
                "id": "m2",
                "title": "NoEv",
                "body": "x",
                "evidence": ["not in the trajectory"],
            },
        ],
    )
    assert [a["id"] for a in result["applied"]] == ["m1"]
    assert result["rejected"][0]["proposal"] == "m2"
    assert result["event"] is not None


def test_refine_with_no_backed_proposals_records_nothing(tmp_path):
    state = _state(tmp_path)
    result = refine(
        state,
        trigger="t",
        trajectory="nothing here",
        proposals=[
            {
                "kind": "memory",
                "id": "m",
                "title": "t",
                "body": "b",
                "evidence": ["absent"],
            }
        ],
    )
    assert result["applied"] == [] and result["event"] is None
    assert state.snapshot_count == 0


def test_refine_rejects_missing_fields(tmp_path):
    state = _state(tmp_path)
    result = refine(
        state,
        trigger="t",
        trajectory="text",
        proposals=[
            {
                "kind": "memory",
                "id": "m",
                "title": "",
                "body": "b",
                "evidence": ["text"],
            }
        ],
    )
    assert "title" in result["rejected"][0]["reason"]


# --- tool family registration ---------------------------------------------------


def test_register_harness_tools_registers_all_six(tmp_path):
    registry = ToolRegistry()
    names = register_harness_tools(registry, tmp_path)
    assert names == list(HARNESS_TOOL_NAMES)
    served = [s["function"]["name"] for s in registry.schemas()]
    for name in HARNESS_TOOL_NAMES:
        assert name in served


def test_disabled_family_registers_nothing(tmp_path):
    registry = ToolRegistry()
    assert register_harness_tools(registry, tmp_path, enabled=False) == []
    assert registry.schemas() == []


def test_write_tools_require_approval(tmp_path):
    registry = ToolRegistry()
    register_harness_tools(registry, tmp_path)
    for name in (
        "harness_upsert",
        "harness_delete",
        "harness_refine",
        "harness_rollback",
    ):
        assert registry.approval_required(name) is True
    for name in ("harness_get", "harness_list"):
        assert registry.approval_required(name) is False


def test_dispatch_upsert_get_roundtrip(tmp_path):
    class _Approvals:
        def is_approved(self, name):
            return True

    registry = ToolRegistry(approval_log=_Approvals())
    register_harness_tools(registry, tmp_path)
    out = json.loads(
        registry.dispatch(
            "harness_upsert",
            {
                "kind": "prompt",
                "id": "p1",
                "title": "T",
                "body": "body",
            },
        )
    )
    assert out["id"] == "p1"
    got = json.loads(registry.dispatch("harness_get", {"kind": "prompt", "id": "p1"}))
    assert got["body"] == "body"
    listed = json.loads(registry.dispatch("harness_list", {"kind": "prompt"}))
    assert [e["id"] for e in listed] == ["p1"]


def test_refine_rollback_restores_durable_entries_and_fixed_prompt(tmp_path):
    from omega_prime.agent.model import ScriptedModel
    from omega_prime.agent.runtime import OmegaPrimeAgent

    class Approvals:
        def is_approved(self, name):
            return True

    registry = ToolRegistry(approval_log=Approvals())
    register_harness_tools(registry, tmp_path)
    before = json.loads(
        registry.dispatch(
            "harness_upsert",
            {
                "kind": "memory",
                "id": "m1",
                "title": "before",
                "body": "prior fact",
                "tags": ["prior"],
            },
        )
    )
    model = ScriptedModel(
        [
            {"role": "assistant", "content": "before refine"},
            {"role": "assistant", "content": "after refine"},
        ]
    )
    with OmegaPrimeAgent(
        model, registry=registry, system_message="Fixed base bytes.\nDo not rewrite."
    ) as agent:
        agent.run("first turn")
        base = model.seen[0][0]["content"].encode()
        registry.dispatch(
            "harness_refine",
            {
                "trigger": "review",
                "trajectory": "observed fact",
                "proposals": [
                    {
                        "kind": "memory",
                        "id": "m1",
                        "title": "after",
                        "body": "new fact",
                        "tags": ["next"],
                        "evidence": ["observed fact"],
                    },
                    {
                        "kind": "skill",
                        "id": "new-skill",
                        "title": "new",
                        "body": "learned rule",
                        "evidence": ["observed fact"],
                    },
                ],
            },
        )
        current = json.loads(
            registry.dispatch("harness_get", {"kind": "memory", "id": "m1"})
        )
        assert current["body"] == "new fact"
        assert json.loads(registry.dispatch("harness_rollback", {}))["restored"] is True
        restored = json.loads(
            registry.dispatch("harness_get", {"kind": "memory", "id": "m1"})
        )
        assert restored == before
        assert "error" in json.loads(
            registry.dispatch("harness_get", {"kind": "skill", "id": "new-skill"})
        )
        agent.run("second turn")
        assert model.seen[1][0]["content"].encode() == base
