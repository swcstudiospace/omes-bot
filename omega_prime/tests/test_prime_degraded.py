"""Tests for Prime degraded mode (LOOP-06): loud-but-non-fatal hook failures."""

from __future__ import annotations

from types import SimpleNamespace

from omega_prime.agent.degraded import guarded_hook
from omega_prime.agent.harness import events_of


def test_successful_hook_returns_result_and_emits_nothing():
    agent = SimpleNamespace()
    result = guarded_hook(agent, "goals", lambda x: x + 1, 41)
    assert result == 42
    assert events_of(agent) == []


def test_failing_hook_emits_structured_event_and_returns_none():
    agent = SimpleNamespace()

    def boom():
        raise RuntimeError("kernel exploded")

    result = guarded_hook(agent, "rlm", boom, turn_id="turn-7")
    assert result is None
    events = events_of(agent)
    assert len(events) == 1
    event = events[0]
    assert event["type"] == "prime_degraded"
    assert event["family"] == "rlm"
    assert "RuntimeError" in event["error"]
    assert "kernel exploded" in event["error"]
    assert event["turn_id"] == "turn-7"


def test_turn_id_generated_when_absent():
    agent = SimpleNamespace()
    guarded_hook(agent, "heartbeat", lambda: 1 / 0)
    event = events_of(agent)[0]
    assert event["turn_id"]
    assert "ZeroDivisionError" in event["error"]


def test_hook_kwargs_pass_through():
    agent = SimpleNamespace()
    result = guarded_hook(agent, "messaging", lambda *, a, b: a * b, a=6, b=7)
    assert result == 42


def test_secret_in_error_is_redacted():
    agent = SimpleNamespace()

    def leaky():
        raise ValueError("token sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAA refused")

    guarded_hook(agent, "autonomous", leaky)
    event = events_of(agent)[0]
    assert "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAA" not in event["error"]
