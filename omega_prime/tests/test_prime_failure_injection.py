"""Failure-injection tests for the Prime connector layer (CONN-03).

Each adapter is driven with a raising capability, a timeout, a malformed
payload, and an unknown status string. Every failure surfaces as a
structured error (PrimeError "code: reason" or the capability module's own
typed error), the degraded-mode wrapper records a ``prime_degraded`` event,
and the loop continues — no hang, no silent drop.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from omega_prime.agent.degraded import guarded_hook
from omega_prime.agent.harness import events_of
from omega_prime.agent.messaging import SessionRegistry
from omega_prime.agent.rlm import NoRlmHost, RlmHost
from omega_prime.prime import PrimeError
from omega_prime.prime.autonomous import AutonomousConnector, StartRequest
from omega_prime.prime.goals import AccrueRequest, GoalsConnector, SetGoalRequest
from omega_prime.prime.harness import UpsertRequest
from omega_prime.prime.messaging import MessagingConnector, SendRequest
from omega_prime.prime.rlm import CollectRequest, RlmConnector, SpawnRequest


class _Parent:
    def __init__(self, tmp_path):
        self.depth = 0
        self.max_depth = 2
        self.max_children = 4
        self.session_dir = str(tmp_path)
        self.session_name = None


# --- raising capability --------------------------------------------------------


def test_raising_capability_degrades_and_loop_continues(tmp_path):
    def explode(prompt, model=None, thinking=None):
        raise RuntimeError("kernel panicked mid-child")

    host = RlmHost(_Parent(tmp_path), run_child=explode)
    connector = RlmConnector(host)
    agent = SimpleNamespace()

    out = guarded_hook(
        agent,
        "rlm",
        lambda: connector.collect(CollectRequest(timeout_ms=0)),
        turn_id="t-1",
    )
    # No children yet: collect of nothing is empty even with a raising runner.
    assert out == {"results": []}

    connector.spawn(SpawnRequest(prompt="boom", name="kid"))
    out = guarded_hook(
        agent,
        "rlm",
        lambda: connector.collect(CollectRequest(timeout_ms=0)),
        turn_id="t-2",
    )
    # The child error is settled into the result, not raised: no degraded event.
    assert out["results"][0]["status"] == "error"
    assert "kernel panicked mid-child" in (out["results"][0]["error"] or "")
    assert events_of(agent) == []

    def hard_raise():
        raise RuntimeError("host exploded")

    assert guarded_hook(agent, "rlm", hard_raise, turn_id="t-3") is None
    event = events_of(agent)[0]
    assert event["type"] == "prime_degraded"
    assert event["family"] == "rlm"
    assert "host exploded" in event["error"]
    # The loop continues: the next guarded call runs fine.
    assert guarded_hook(agent, "rlm", lambda: "ok") == "ok"


def test_no_host_spawn_raises_verbatim_and_degrades(tmp_path):
    connector = RlmConnector(NoRlmHost())
    agent = SimpleNamespace()
    out = guarded_hook(
        agent, "rlm", lambda: connector.spawn(SpawnRequest(prompt="x", name="y"))
    )
    assert out is None
    event = events_of(agent)[0]
    assert event["type"] == "prime_degraded"
    assert "no RLM child runtime" in event["error"]


# --- timeout ---------------------------------------------------------------------


def test_collect_timeout_returns_snapshots_not_hang(tmp_path):
    def slow(prompt, model=None, thinking=None):
        time.sleep(2.0)
        return "late"

    host = RlmHost(_Parent(tmp_path), run_child=slow)
    connector = RlmConnector(host)
    connector.spawn(SpawnRequest(prompt="slow work", name="kid"))
    started = time.monotonic()
    out = connector.collect(CollectRequest(timeout_ms=50))
    elapsed = time.monotonic() - started
    assert elapsed < 1.0  # no hang: the timeout is honored
    assert out["results"][0]["status"] in ("running", "queued")
    assert out["results"][0]["settled"] is False


# --- malformed payload ----------------------------------------------------------


def test_malformed_payloads_are_typed_errors_not_tracebacks(tmp_path):
    with pytest.raises(PrimeError, match="bad_type"):
        UpsertRequest.from_dict(["not", "an", "object"])
    with pytest.raises(PrimeError, match="unknown_field"):
        UpsertRequest.from_dict(
            {"kind": "prompt", "id": "i", "title": "t", "body": "b", "payload": {}}
        )
    goals = GoalsConnector(tmp_path / "goals")
    goals.set_goal(SetGoalRequest(objective="x", token_budget=100))
    # A non-dict usage is rejected at the typed boundary...
    with pytest.raises(PrimeError, match="bad_type"):
        AccrueRequest.from_dict({"usage": "lots"})
    # ...while a dict with junk values is the capability's tolerance: delta 0,
    # no raise, no accrual (goal_token_delta_for_usage ignores non-ints).
    out = goals.accrue(AccrueRequest(usage={"total_tokens": "lots"}))
    assert out["tokens_used"] == 0


def test_messaging_malformed_then_recovers():
    connector = MessagingConnector(SessionRegistry())
    connector._registry.register("a")
    connector._registry.register("b")
    with pytest.raises(PrimeError, match="bad_type"):
        SendRequest.from_dict({"sender": "a", "recipient": "b", "body": 12})
    # The registry is unharmed; a well-formed send still lands.
    out = connector.send(SendRequest(sender="a", recipient="b", body="still here"))
    assert "delivered" in out


# --- unknown status string -------------------------------------------------------


def test_unknown_status_string_rejected_at_the_boundary(tmp_path):
    connector = GoalsConnector(tmp_path / "goals")
    connector.set_goal(SetGoalRequest(objective="x"))
    # Corrupt the sidecar with an out-of-vocabulary status.
    import json

    sidecar = tmp_path / "goals" / "prime_goal.json"
    document = json.loads(sidecar.read_text())
    document["status"] = "teleported"
    sidecar.write_text(json.dumps(document))
    with pytest.raises(PrimeError, match="prime_status"):
        connector.status()


def test_autonomous_gate_failure_is_a_structured_stop(tmp_path):
    connector = AutonomousConnector(tmp_path)
    driver = connector.start(StartRequest(gate=("false",), gate_retries=1))
    verdict = connector.after_turn(driver, {"completed": True, "usage": {}})
    assert verdict["action"] == "stop"
    assert verdict["reason"] == "autonomous_gate_failed"
    # A stopped driver stays stopped — no hang, no restart.
    assert (
        connector.after_turn(driver, {"completed": True})["reason"]
        == "autonomous_gate_failed"
    )
