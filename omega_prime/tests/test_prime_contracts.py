"""Contract tests for the Prime connector layer (CONN-01, CONN-02).

Both sides of each adapter: the tool surface (JSON dicts in) and the
capability surface (typed views out). Round-trips are lossless; malformed
payloads — unknown fields, bool/int confusion, out-of-vocabulary values,
future schema versions — are rejected with typed PrimeErrors.
"""

from __future__ import annotations

import pytest

from omega_prime.agent.messaging import SessionRegistry
from omega_prime.agent.rlm import RlmHost
from omega_prime.prime import SCHEMA_VERSION, PrimeError
from omega_prime.prime.autonomous import AutonomousConnector, StartRequest, VerdictView
from omega_prime.prime.goals import (
    AccrueRequest,
    GoalsConnector,
    GoalStatusView,
    SetGoalRequest,
)
from omega_prime.prime.harness import EntryView, HarnessConnector, UpsertRequest
from omega_prime.prime.messaging import MessageView, MessagingConnector, SendRequest
from omega_prime.prime.rlm import (
    ChildResultView,
    CollectRequest,
    ProgressNoteRequest,
    RlmConnector,
    SpawnRequest,
)


class _Parent:
    def __init__(self, tmp_path):
        self.depth = 0
        self.max_depth = 2
        self.max_children = 4
        self.session_dir = str(tmp_path)
        self.session_name = None


def _rlm_connector(tmp_path):
    host = RlmHost(
        _Parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: f"done: {prompt}",
    )
    return RlmConnector(host)


# --- schema version guard ----------------------------------------------------


@pytest.mark.parametrize(
    "cls,payload",
    [
        (SpawnRequest, {"prompt": "p", "name": "n"}),
        (CollectRequest, {}),
        (ProgressNoteRequest, {"child_id": "c", "message": "m"}),
        (UpsertRequest, {"kind": "prompt", "id": "i", "title": "t", "body": "b"}),
        (SetGoalRequest, {"objective": "o"}),
        (AccrueRequest, {"usage": {}}),
        (StartRequest, {}),
        (SendRequest, {"sender": "a", "recipient": "b", "body": "x"}),
    ],
)
def test_future_schema_version_rejected_everywhere(cls, payload):
    with pytest.raises(PrimeError, match="unsupported_schema_version"):
        cls.from_dict({**payload, "schema_version": SCHEMA_VERSION + 1})


def test_current_schema_version_accepted():
    request = SpawnRequest.from_dict(
        {"prompt": "p", "name": "n", "schema_version": SCHEMA_VERSION}
    )
    assert request.to_dict()["schema_version"] == SCHEMA_VERSION


def test_non_int_schema_version_rejected():
    with pytest.raises(PrimeError, match="schema_version must be int"):
        SpawnRequest.from_dict({"prompt": "p", "name": "n", "schema_version": "1"})


# --- rlm ----------------------------------------------------------------------


def test_spawn_request_round_trip():
    request = SpawnRequest.from_dict({"prompt": "do it", "name": "kid", "model": "m"})
    assert SpawnRequest.from_dict(request.to_dict()) == request


def test_spawn_request_rejects_unknown_field():
    with pytest.raises(PrimeError, match="unknown_field"):
        SpawnRequest.from_dict({"prompt": "p", "name": "n", "surprise": 1})


def test_spawn_request_rejects_bool_model():
    with pytest.raises(PrimeError, match="bad_type"):
        SpawnRequest.from_dict({"prompt": "p", "name": "n", "model": True})


def test_collect_request_validates_targets():
    with pytest.raises(PrimeError, match="targets must be"):
        CollectRequest.from_dict({"targets": 42})
    with pytest.raises(PrimeError, match="entries must be strings"):
        CollectRequest.from_dict({"targets": ["ok", 7]})
    assert CollectRequest.from_dict({"targets": ["a"], "timeout_ms": 5}).timeout_ms == 5


def test_rlm_connector_spawn_collect_round_trip(tmp_path):
    connector = _rlm_connector(tmp_path)
    spawned = connector.spawn(SpawnRequest(prompt="work", name="kid"))
    assert spawned["rlm_child_id"].startswith("rlm-")
    out = connector.collect(CollectRequest(targets=["kid"], timeout_ms=5000))
    assert out["results"][0]["status"] == "done"
    assert out["results"][0]["settled"] is True
    # The tool-surface dict decodes back into the typed view losslessly.
    view = ChildResultView.from_dict(out["results"][0])
    assert view.to_dict() == out["results"][0]


def test_child_result_view_rejects_unknown_status():
    with pytest.raises(PrimeError, match="not in COLLECT_STATUSES"):
        ChildResultView.from_dict(
            {"rlm_child_id": "x", "status": "teleported", "settled": True}
        )


# --- harness --------------------------------------------------------------------


def test_upsert_request_round_trip():
    request = UpsertRequest.from_dict(
        {
            "kind": "skill",
            "id": "s1",
            "title": "T",
            "body": "B",
            "scope": "global",
            "tags": ["a"],
        }
    )
    assert request.scope == "global"
    assert UpsertRequest.from_dict(request.to_dict()) == request


def test_upsert_request_rejects_unknown_kind():
    with pytest.raises(PrimeError, match="must be one of"):
        UpsertRequest.from_dict(
            {"kind": "widget", "id": "i", "title": "t", "body": "b"}
        )


def test_harness_connector_round_trip(tmp_path):
    connector = HarnessConnector(tmp_path)
    connector.upsert(UpsertRequest(kind="memory", id="m1", title="T", body="B"))
    got = connector.get("memory", "m1")
    assert got["entry"]["body"] == "B"
    view = EntryView.from_dict(got["entry"])
    assert view.to_dict() == got["entry"]
    assert connector.list_entries("memory")["entries"][0]["id"] == "m1"
    assert connector.delete("memory", "m1") == {"deleted": True}


# --- goals ----------------------------------------------------------------------


def test_set_goal_request_rejects_bool_budget():
    with pytest.raises(PrimeError, match="bad_type"):
        SetGoalRequest.from_dict({"objective": "o", "token_budget": True})


def test_goals_connector_lifecycle(tmp_path):
    connector = GoalsConnector(tmp_path / "goals")
    connector.set_goal(
        SetGoalRequest(objective="ship it", token_budget=100, steps=("a", "b"))
    )
    status = connector.status()
    assert status["prime_status"] == "active"
    assert status["token_budget"] == 100
    view = GoalStatusView.from_dict(status)
    assert view.to_dict() == status
    connector.accrue(AccrueRequest(usage={"total_tokens": 40}))
    assert connector.status()["tokens_used"] == 40
    assert connector.continuation_prompt()["prompt"].startswith(
        "Continue working toward"
    )


def test_goal_status_view_rejects_unknown_status():
    with pytest.raises(PrimeError, match="prime_status"):
        GoalStatusView.from_dict({"objective": "o", "prime_status": "vibing"})


# --- autonomous -------------------------------------------------------------------


def test_start_request_rejects_shell_string_gate():
    with pytest.raises(PrimeError, match="argv list"):
        StartRequest.from_dict({"gate": "make test"})


def test_start_request_round_trip():
    request = StartRequest.from_dict(
        {"max_turns": 3, "gate": ["true"], "gate_retries": 0, "max_minutes": 1.5}
    )
    assert request.gate == ("true",)
    assert StartRequest.from_dict(request.to_dict()) == request


def test_autonomous_connector_verdict_typing(tmp_path):
    connector = AutonomousConnector(tmp_path)
    driver = connector.start(StartRequest(max_turns=1))
    verdict = connector.after_turn(
        driver, {"completed": False, "usage": {"total_tokens": 5}}
    )
    assert verdict["action"] == "stop"
    assert verdict["reason"] == "autonomous_max_turns"
    view = VerdictView.from_dict(verdict)
    assert view.to_dict() == verdict


def test_verdict_view_rejects_unknown_stop_reason():
    with pytest.raises(PrimeError, match=r"not in STOP_REASONS|must be one of"):
        VerdictView.from_dict({"action": "stop", "reason": "autonomous_bored"})


# --- messaging ------------------------------------------------------------------


def test_send_request_rejects_empty_body():
    with pytest.raises(PrimeError, match="non-empty string"):
        SendRequest.from_dict({"sender": "a", "recipient": "b", "body": ""})


def test_messaging_connector_round_trip():
    connector = MessagingConnector(SessionRegistry())
    connector._registry.register("alpha")
    connector._registry.register("beta")
    out = connector.send(SendRequest(sender="alpha", recipient="beta", body="ping"))
    delivered = out["delivered"]
    view = MessageView.from_dict(delivered)
    assert view.to_dict() == delivered
    inbox = connector.observe("beta")
    assert inbox["messages"][0]["body"] == "ping"
    assert inbox["messages"][0]["read"] is True


def test_messaging_connector_unknown_recipient_raises():
    connector = MessagingConnector(SessionRegistry())
    connector._registry.register("alpha")
    with pytest.raises(PrimeError) as excinfo:
        connector.send(SendRequest(sender="alpha", recipient="ghost", body="hi"))
    assert excinfo.value.code == "unknown_recipient"
    assert "ghost" in str(excinfo.value)
