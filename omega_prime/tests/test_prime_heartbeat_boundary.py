# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""The heartbeat family decodes through a typed, versioned boundary (CONN-01).

Every case dispatches through the real registry (real ``ApprovalLog`` grants by
a named reviewer) or the real ``OmegaPrimeAgent.run`` loop with a scripted
model. A malformed, future-versioned or unknown-field request surfaces as a
typed error code and persists nothing; no scheduler is started.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from omega_prime.agent.model import ScriptedModel
from omega_prime.agent.runtime import OmegaPrimeAgent
from omega_prime.prime.heartbeat import (
    SCHEMA_VERSION,
    ClearRequest,
    ListRequest,
    SetRequest,
)
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.heartbeat import HEARTBEAT_TOOL_NAMES, register_heartbeat_tools
from omega_prime.tools.registry import ToolRegistry


def _granted(*families):
    """A registry whose tools carry real human grants, nothing else."""
    log = ApprovalLog()
    for family in families:
        for name in family:
            receipt = log.approve(name, "phase61-human-reviewer")
            assert receipt["approved"] is True
    return ToolRegistry(approval_log=log)


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


def _close(registry) -> None:
    runtime = registry.runtime_bindings.get("prime_heartbeat")
    if runtime is not None:
        runtime.close()


@pytest.fixture
def registry(tmp_path) -> Iterator[ToolRegistry]:
    granted = _granted(HEARTBEAT_TOOL_NAMES)
    register_heartbeat_tools(granted, tmp_path)
    try:
        yield granted
    finally:
        _close(granted)


def _jobs_file(tmp_path):
    return tmp_path / "cron" / "jobs.json"


def _dispatch(registry, name, arguments):
    return json.loads(registry.dispatch(name, arguments))


def _set_args(**overrides):
    arguments = {"session": "sess", "prompt": "beat", "interval_seconds": 30}
    arguments.update(overrides)
    return arguments


def test_valid_set_list_clear_round_trip(registry, tmp_path):
    scheduled = _dispatch(registry, "heartbeat_set", _set_args(schema_version=1))
    assert scheduled["session"] == "sess"
    job_id = scheduled["scheduled"]

    listed = _dispatch(registry, "heartbeat_list", {"schema_version": 1})
    assert [job["id"] for job in listed] == [job_id]
    assert listed[0]["session"] == "sess"
    assert listed[0]["interval_seconds"] == 30

    cleared = _dispatch(registry, "heartbeat_clear", {"job_id": job_id})
    assert cleared == {"cleared": job_id}
    assert _dispatch(registry, "heartbeat_list", {}) == []
    assert _jobs_file(tmp_path).exists()


def test_empty_prompt_and_explicit_due_at_are_accepted(registry):
    scheduled = _dispatch(
        registry,
        "heartbeat_set",
        _set_args(prompt="", due_at=1_900_000_000.5, interval_seconds=0.5),
    )
    listed = _dispatch(registry, "heartbeat_list", {})
    assert [job["id"] for job in listed] == [scheduled["scheduled"]]
    assert listed[0]["due_at"] == 1_900_000_000.5


@pytest.mark.parametrize(
    ("interval", "code"),
    [
        (True, "bad_type"),
        (False, "bad_type"),
        ("30", "bad_type"),
        (None, "bad_type"),
        (float("nan"), "bad_value"),
        (float("inf"), "bad_value"),
        (float("-inf"), "bad_value"),
        (0, "bad_value"),
        (-5, "bad_value"),
    ],
)
def test_bad_interval_is_typed_and_persists_nothing(registry, tmp_path, interval, code):
    result = _dispatch(registry, "heartbeat_set", _set_args(interval_seconds=interval))

    assert result["code"] == code
    assert result["error"].startswith(code)
    assert not _jobs_file(tmp_path).exists()
    assert _dispatch(registry, "heartbeat_list", {}) == []


@pytest.mark.parametrize(
    ("due_at", "code"),
    [
        (True, "bad_type"),
        ("soon", "bad_type"),
        (float("nan"), "bad_value"),
        (float("inf"), "bad_value"),
    ],
)
def test_bad_due_at_is_typed_and_persists_nothing(registry, tmp_path, due_at, code):
    result = _dispatch(registry, "heartbeat_set", _set_args(due_at=due_at))

    assert result["code"] == code
    assert not _jobs_file(tmp_path).exists()


def test_deadline_beyond_scheduler_calendar_is_bad_value(registry, tmp_path):
    result = _dispatch(registry, "heartbeat_set", _set_args(due_at=1e18))

    assert result["code"] == "bad_value"
    assert result["error"].startswith("bad_value")
    assert not _jobs_file(tmp_path).exists()


@pytest.mark.parametrize("session", ["", "   ", 7, True])
def test_bad_session_is_bad_type_and_persists_nothing(registry, tmp_path, session):
    result = _dispatch(registry, "heartbeat_set", _set_args(session=session))

    assert result["code"] == "bad_type"
    assert not _jobs_file(tmp_path).exists()


def test_non_string_prompt_is_bad_type_and_persists_nothing(registry, tmp_path):
    result = _dispatch(registry, "heartbeat_set", _set_args(prompt=12))

    assert result["code"] == "bad_type"
    assert not _jobs_file(tmp_path).exists()


@pytest.mark.parametrize("missing", ["session", "prompt", "interval_seconds"])
def test_omitted_required_field_is_bad_type(registry, tmp_path, missing):
    arguments = _set_args()
    del arguments[missing]

    result = _dispatch(registry, "heartbeat_set", arguments)

    assert result["code"] == "bad_type"
    assert not _jobs_file(tmp_path).exists()


def test_clear_without_or_with_bad_job_id_is_bad_type(registry):
    scheduled = _dispatch(registry, "heartbeat_set", _set_args())

    for arguments in ({}, {"job_id": ""}, {"job_id": 5}, {"job_id": None}):
        assert _dispatch(registry, "heartbeat_clear", arguments)["code"] == "bad_type"

    listed = _dispatch(registry, "heartbeat_list", {})
    assert [job["id"] for job in listed] == [scheduled["scheduled"]]


@pytest.mark.parametrize("version", [2, 99])
def test_future_schema_version_is_unsupported_everywhere(registry, tmp_path, version):
    job = _dispatch(registry, "heartbeat_set", _set_args())["scheduled"]
    before = _jobs_file(tmp_path).read_bytes()

    calls = [
        ("heartbeat_set", _set_args(schema_version=version)),
        ("heartbeat_list", {"schema_version": version}),
        ("heartbeat_clear", {"job_id": job, "schema_version": version}),
    ]
    for name, arguments in calls:
        result = _dispatch(registry, name, arguments)
        assert result["code"] == "unsupported_schema_version", name

    assert _jobs_file(tmp_path).read_bytes() == before


def test_future_schema_version_on_set_persists_nothing(registry, tmp_path):
    result = _dispatch(registry, "heartbeat_set", _set_args(schema_version=2))

    assert result["code"] == "unsupported_schema_version"
    assert not _jobs_file(tmp_path).exists()


@pytest.mark.parametrize("version", [0, -1])
def test_non_positive_schema_version_is_bad_value(registry, tmp_path, version):
    result = _dispatch(registry, "heartbeat_set", _set_args(schema_version=version))

    assert result["code"] == "bad_value"
    assert not _jobs_file(tmp_path).exists()


def test_unknown_field_is_typed_everywhere_and_persists_nothing(registry, tmp_path):
    job = _dispatch(registry, "heartbeat_set", _set_args())["scheduled"]
    before = _jobs_file(tmp_path).read_bytes()

    calls = [
        ("heartbeat_set", _set_args(owner="mallory")),
        ("heartbeat_list", {"verbose": True}),
        ("heartbeat_clear", {"job_id": job, "force": True}),
    ]
    for name, arguments in calls:
        result = _dispatch(registry, name, arguments)
        assert result["code"] == "unknown_field", name
        assert result["error"].startswith("unknown_field"), name

    assert _jobs_file(tmp_path).read_bytes() == before
    assert [j["id"] for j in _dispatch(registry, "heartbeat_list", {})] == [job]


def test_unapproved_malformed_set_is_denied_before_decode(tmp_path):
    log = ApprovalLog()
    assert log.approve("heartbeat_list", "phase61-human-reviewer")["approved"] is True
    registry = ToolRegistry(approval_log=log)
    register_heartbeat_tools(registry, tmp_path)
    try:
        malformed = [
            _set_args(interval_seconds=True),
            _set_args(schema_version=9),
            _set_args(owner="x"),
            {},
        ]
        for arguments in malformed:
            result = _dispatch(registry, "heartbeat_set", arguments)
            assert result["error"] == "approval required"
            assert "code" not in result
        denied_clear = _dispatch(registry, "heartbeat_clear", {"job_id": 5})
        assert denied_clear["error"] == "approval required"

        assert not _jobs_file(tmp_path).exists()
    finally:
        _close(registry)


def test_loop_sees_typed_error_for_malformed_set_then_recovers(registry):
    agent, result = _run(
        registry,
        [
            _tool_call(
                "heartbeat_set",
                '{"session": "sess", "prompt": "beat", "interval_seconds": true}',
                "call-bad-type",
            ),
            _tool_call(
                "heartbeat_set",
                '{"session": "sess", "prompt": "beat", "interval_seconds": 0}',
                "call-bad-value",
            ),
            _tool_call(
                "heartbeat_set",
                '{"session": "sess", "prompt": "beat", "interval_seconds": 30,'
                ' "schema_version": 2}',
                "call-future",
            ),
            _tool_call(
                "heartbeat_set",
                '{"session": "sess", "prompt": "beat", "interval_seconds": 30}',
                "call-good",
            ),
            {"role": "assistant", "content": "recovered"},
        ],
    )

    assert result["final_response"] == "recovered"
    for call_id, code in (
        ("call-bad-type", "bad_type"),
        ("call-bad-value", "bad_value"),
        ("call-future", "unsupported_schema_version"),
    ):
        content = _model_tool_content(agent, call_id)
        assert content.startswith("error:"), call_id
        assert code in content, call_id
    good = _model_tool_payload(agent, "call-good")
    assert good["session"] == "sess"
    listed = _dispatch(registry, "heartbeat_list", {})
    assert [job["id"] for job in listed] == [good["scheduled"]]
    agent.close()


@pytest.mark.parametrize(
    "request_",
    [
        SetRequest(session="sess", prompt="beat", interval_seconds=30),
        SetRequest(session="sess", prompt="beat", interval_seconds=0.5, due_at=12.5),
        SetRequest(session="sess", prompt="", interval_seconds=1, due_at=0),
        ClearRequest(job_id="abc123"),
        ListRequest(),
    ],
)
def test_request_round_trips_through_its_wire_form(request_):
    wire = request_.to_dict()

    assert wire["schema_version"] == SCHEMA_VERSION
    assert type(request_).from_dict(wire) == request_
