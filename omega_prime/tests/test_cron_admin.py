"""Tests for the cron admin tool family. Hermetic."""

from __future__ import annotations

import json

from omega_prime.cron.heartbeat import HEARTBEAT_KIND, list_heartbeats
from omega_prime.cron.scheduler import DESK_LEAD_KIND, JobStore, list_desk_lead_passes
from omega_prime.tools.cron_admin import (
    _WRITE_TOOLS,
    CRON_ADMIN_TOOL_NAMES,
    register_cron_admin_tools,
)
from omega_prime.tools.registry import ToolRegistry

STORE_PATH_COMPONENTS = ("cron", "jobs.json")


class _Approvals:
    def is_approved(self, name):
        return True


def _registry(tmp_path):
    registry = ToolRegistry(approval_log=_Approvals())
    names = register_cron_admin_tools(registry, tmp_path)
    assert names == list(CRON_ADMIN_TOOL_NAMES)
    return registry


def _dispatch(registry, name, arguments):
    return json.loads(registry.dispatch(name, arguments))


def _store(tmp_path):
    return JobStore(tmp_path.joinpath(*STORE_PATH_COMPONENTS))


def test_write_tools_declared_and_gated(tmp_path):
    assert CRON_ADMIN_TOOL_NAMES == (
        "cron_jobs_list",
        "cron_job_create",
        "cron_job_remove",
    )
    assert frozenset({"cron_job_create", "cron_job_remove"}) == _WRITE_TOOLS
    assert set(CRON_ADMIN_TOOL_NAMES) >= _WRITE_TOOLS

    registry = _registry(tmp_path)
    for name in _WRITE_TOOLS:
        assert registry.approval_required(name) is True
    assert registry.approval_required("cron_jobs_list") is False

    # Without an approval log the write tools never run.
    bare = ToolRegistry()
    register_cron_admin_tools(bare, tmp_path)
    denied = _dispatch(bare, "cron_job_create", {"prompt": "nope"})
    assert denied == {"error": "approval required", "tool": "cron_job_create"}


def test_list_empty_store(tmp_path):
    registry = _registry(tmp_path)
    listed = _dispatch(registry, "cron_jobs_list", {})
    assert listed == {"jobs": [], "count": 0}
    # No store file was invented for a read.
    assert not tmp_path.joinpath(*STORE_PATH_COMPONENTS).exists()


def test_create_then_list_through_stores_own_loader(tmp_path):
    registry = _registry(tmp_path)
    created = _dispatch(
        registry,
        "cron_job_create",
        {"prompt": "water the plants", "due_at": 1000, "interval_seconds": 60},
    )
    assert created["kind"] == "prompt"
    assert created["due_at"] == 1000
    assert created["interval_seconds"] == 60
    job_id = created["created"]

    # The store's own loader (the same file the scheduler ticks) sees it,
    # stored as a plain job with no kind key, exactly as JobStore.schedule
    # writes it.
    reloaded = _store(tmp_path)
    assert [job["id"] for job in reloaded.jobs] == [job_id]
    assert reloaded.jobs[0]["prompt"] == "water the plants"
    assert reloaded.jobs[0]["due_at"] == 1000
    assert reloaded.jobs[0]["interval_seconds"] == 60
    assert "kind" not in reloaded.jobs[0]

    listed = _dispatch(registry, "cron_jobs_list", {})
    assert listed["count"] == 1
    row = listed["jobs"][0]
    assert row["id"] == job_id
    assert row["kind"] == "prompt"
    assert row["prompt"] == "water the plants"
    assert row["due_at"] == 1000
    assert row["interval_seconds"] == 60
    assert row["completed"] is False
    assert row["next_due_at"] == 1000


def test_create_one_shot_prompt_job_defaults_interval(tmp_path):
    registry = _registry(tmp_path)
    created = _dispatch(registry, "cron_job_create", {"prompt": "once", "due_at": 2000})
    assert created["interval_seconds"] is None
    reloaded = _store(tmp_path)
    assert reloaded.jobs[0]["interval_seconds"] is None
    # A completed one-shot has no next due.
    reloaded.jobs[0]["completed"] = True
    reloaded._save()
    row = _dispatch(registry, "cron_jobs_list", {})["jobs"][0]
    assert row["completed"] is True
    assert row["next_due_at"] is None


def test_create_kind_jobs_reuse_the_kinds_own_writers(tmp_path):
    registry = _registry(tmp_path)
    desk = _dispatch(
        registry,
        "cron_job_create",
        {
            "kind": "desk_lead_pass",
            "prompt": "run one desk lead pass",
            "due_at": 1000,
            "interval_seconds": 60,
            "intake_path": str(tmp_path / "intake.json"),
            "limit": 2,
        },
    )
    beat = _dispatch(
        registry,
        "cron_job_create",
        {
            "kind": "session_heartbeat",
            "prompt": "check in",
            "due_at": 1500,
            "interval_seconds": 30,
            "session": "sess-1",
        },
    )
    # The kind-owning scheduler helpers see them (same store, same writers).
    passes = list_desk_lead_passes(_store(tmp_path))
    assert [job["id"] for job in passes] == [desk["created"]]
    assert passes[0]["kind"] == DESK_LEAD_KIND
    assert passes[0]["intake_path"] == str(tmp_path / "intake.json")
    assert passes[0]["limit"] == 2
    beats = list_heartbeats(_store(tmp_path))
    assert [job["id"] for job in beats] == [beat["created"]]
    assert beats[0]["kind"] == HEARTBEAT_KIND
    assert beats[0]["session"] == "sess-1"
    kinds = {
        row["kind"]: row for row in _dispatch(registry, "cron_jobs_list", {})["jobs"]
    }
    assert set(kinds) == {"desk_lead_pass", "session_heartbeat"}


def test_remove_then_gone(tmp_path):
    registry = _registry(tmp_path)
    job_id = _dispatch(registry, "cron_job_create", {"prompt": "bye", "due_at": 1000})[
        "created"
    ]
    removed = _dispatch(registry, "cron_job_remove", {"job_id": job_id})
    assert removed == {"removed": job_id, "kind": "prompt"}
    assert _store(tmp_path).jobs == []
    assert _dispatch(registry, "cron_jobs_list", {}) == {"jobs": [], "count": 0}
    # Unknown id is an explicit error dict, not a raise.
    missing = _dispatch(registry, "cron_job_remove", {"job_id": "nope"})
    assert "error" in missing


def test_bad_kind_rejected_as_dict(tmp_path):
    registry = _registry(tmp_path)
    result = _dispatch(
        registry, "cron_job_create", {"kind": "wat", "prompt": "p", "due_at": 1}
    )
    assert result["error"] == "unsupported cron kind 'wat'"
    assert set(result["reason"].split(": ")[1].split(", ")) == {
        "prompt",
        "desk_lead_pass",
        "session_heartbeat",
    }
    assert not tmp_path.joinpath(*STORE_PATH_COMPONENTS).exists()


def test_bad_schedule_rejected_as_dict(tmp_path):
    registry = _registry(tmp_path)
    bad = [
        {"prompt": "p", "interval_seconds": 0},  # non-positive interval
        {"prompt": "p", "interval_seconds": -5},
        {"prompt": "p", "interval_seconds": True},  # bool is not a schedule
        {"prompt": "p", "due_at": "soon"},  # non-numeric due_at
        {"prompt": "   "},  # blank prompt
        {"kind": "desk_lead_pass", "prompt": "p", "due_at": 1},  # desk: no interval
        {  # heartbeat: no session
            "kind": "session_heartbeat",
            "prompt": "p",
            "due_at": 1,
            "interval_seconds": 30,
        },
        {  # wrong-kind extras are refused, not silently dropped
            "prompt": "p",
            "due_at": 1,
            "session": "sess",
        },
    ]
    for arguments in bad:
        result = _dispatch(registry, "cron_job_create", arguments)
        assert isinstance(result, dict) and "error" in result, (arguments, result)
    assert not tmp_path.joinpath(*STORE_PATH_COMPONENTS).exists()

    # Bad remove arguments too.
    assert "error" in _dispatch(registry, "cron_job_remove", {"job_id": ""})
    assert "error" in _dispatch(registry, "cron_job_remove", {})


def test_unknown_arguments_rejected(tmp_path):
    registry = _registry(tmp_path)
    result = _dispatch(registry, "cron_jobs_list", {"nope": 1})
    assert result["code"] == "unknown_field"
    assert "error" in result and "reason" in result
    created = _dispatch(
        registry,
        "cron_job_create",
        {"prompt": "p", "due_at": 1, "nope": 1},
    )
    assert created["code"] == "unknown_field"
    assert not tmp_path.joinpath(*STORE_PATH_COMPONENTS).exists()


def test_unreadable_store_is_an_explicit_error(tmp_path):
    registry = _registry(tmp_path)
    store_path = tmp_path.joinpath(*STORE_PATH_COMPONENTS)
    store_path.parent.mkdir(parents=True)
    store_path.write_text("{not json", encoding="utf-8")
    listed = _dispatch(registry, "cron_jobs_list", {})
    assert "error" in listed
    assert "cron_jobs_list" not in listed
