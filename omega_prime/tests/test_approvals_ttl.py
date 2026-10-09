# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""ApprovalLog TTL, revoke and entries behavior (63-03)."""

from __future__ import annotations

import threading

import pytest

from omega_prime.tools.approvals import ApprovalLog


class _Clock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_backward_compatible_return_shape() -> None:
    log = ApprovalLog()
    assert log.approve("t", "alice") == {
        "approved": True,
        "tool": "t",
        "approved_by": "alice",
        "bot_id": "bot-00-omega-prime",
    }
    assert log.is_approved("t")
    assert not log.is_approved("other")
    assert not log.is_approved(None)  # type: ignore[arg-type]


def test_approval_without_ttl_never_expires() -> None:
    clock = _Clock()
    log = ApprovalLog(clock=clock)
    log.approve("t", "alice")
    clock.now += 10**9
    assert log.is_approved("t")
    assert log.entries()[0]["expires_at"] is None


def test_ttl_adds_expires_at_and_expires() -> None:
    clock = _Clock()
    log = ApprovalLog(clock=clock)
    result = log.approve("t", "alice", ttl_seconds=60)
    assert result["approved"] is True
    assert result["expires_at"] == 1060.0
    clock.now = 1059.9
    assert log.is_approved("t")
    clock.now = 1060.0
    assert not log.is_approved("t")
    assert log.entries() == []
    assert log.revoke("t") is False


def test_reapprove_replaces_ttl() -> None:
    clock = _Clock()
    log = ApprovalLog(clock=clock)
    log.approve("t", "alice", ttl_seconds=10)
    clock.now += 5
    log.approve("t", "carol", ttl_seconds=100)
    clock.now += 50
    assert log.is_approved("t")
    (entry,) = log.entries()
    assert entry["approved_by"] == "carol"
    assert entry["approved_at"] == 1005.0
    assert entry["expires_at"] == 1105.0


def test_revoke() -> None:
    log = ApprovalLog()
    log.approve("t", "alice")
    assert log.revoke("t") is True
    assert not log.is_approved("t")
    assert log.revoke("t") is False
    assert log.revoke(None) is False  # type: ignore[arg-type]


def test_entries_sorted_and_shaped() -> None:
    clock = _Clock()
    log = ApprovalLog(clock=clock)
    log.approve("zeta", "alice")
    log.approve("alpha", "bob", ttl_seconds=5)
    entries = log.entries()
    assert [e["tool"] for e in entries] == ["alpha", "zeta"]
    assert entries[0] == {
        "tool": "alpha",
        "approved_by": "bob",
        "approved_at": 1000.0,
        "expires_at": 1005.0,
    }
    assert set(entries[1]) == {"tool", "approved_by", "approved_at", "expires_at"}
    entries[0]["tool"] = "mutated"
    assert log.entries()[0]["tool"] == "alpha"


@pytest.mark.parametrize(
    "ttl", [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), True, "60"]
)
def test_bad_ttl_is_error_result_not_exception(ttl: object) -> None:
    log = ApprovalLog()
    result = log.approve("t", "alice", ttl_seconds=ttl)  # type: ignore[arg-type]
    assert result["approved"] is False
    assert "ttl_seconds" in result["error"]
    assert not log.is_approved("t")


def test_existing_validation_unchanged() -> None:
    log = ApprovalLog()
    assert log.approve("", "alice")["approved"] is False
    assert log.approve("t", " ")["approved"] is False
    assert log.approve("t", "alice", bot_id="")["approved"] is False
    refused = log.approve("t", "bot-00-omega-prime")
    assert refused == {"approved": False, "error": "approved_by must not be the bot"}
    assert log.entries() == []


def test_thread_safety_smoke() -> None:
    log = ApprovalLog()
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            for round_ in range(200):
                name = f"tool-{index}-{round_ % 5}"
                log.approve(name, "alice", ttl_seconds=100)
                log.is_approved(name)
                log.entries()
                log.revoke(name)
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert log.entries() == []
