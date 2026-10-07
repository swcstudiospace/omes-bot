"""Phase 23: adversarial battery through the real PyRIT send path."""

from __future__ import annotations

import json
from pathlib import Path

from pyrit.models.messages.message import Message

from omes.evals.pyrit_target import (
    OmesPromptTarget,
    message_text,
    registry_responder,
    run_battery,
)
from omes.policy.policy import SeatPolicy
from omes.tools.approvals import ApprovalLog
from omes.tools.registry import ToolRegistry

CASES = json.loads(
    (
        Path(__file__).resolve().parent.parent / "evals" / "cases" / "adversarial.json"
    ).read_text(encoding="utf-8")
)


def _registry() -> tuple[ToolRegistry, ApprovalLog, list]:
    calls: list = []
    policy = SeatPolicy(
        {"version": 1, "tools": {"allow": ["x_post"]}, "paths": {}, "network": {}}
    )
    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log, policy=policy)
    registry.register(
        "x_post",
        "publish stub",
        {"type": "object", "properties": {}},
        lambda text="": {"posted": True, "text": text},
        requires_approval=True,
    )

    def _canary() -> str:
        calls.append("canary")
        return "canary-ran"

    registry.register(
        "canary", "must never run", {"type": "object", "properties": {}}, _canary
    )
    return registry, log, calls


def test_battery_refusals_hold_through_pyrit():
    registry, _, calls = _registry()
    target = OmesPromptTarget(respond=registry_responder(registry))
    rows = run_battery(target, [case["prompt"] for case in CASES])
    assert [row["prompt"] for row in rows] == [case["prompt"] for case in CASES]
    for case, row in zip(CASES, rows, strict=True):
        for text in case["must_contain"]:
            assert text in row["response"], (
                f"{case['id']} lacks {text!r}: {row['response']!r}"
            )
        for text in case["must_not_contain"]:
            assert text not in row["response"], f"{case['id']} leaks {text!r}"
    assert calls == []


def test_approved_dispatch_is_not_a_refusal_stub():
    registry, log, _ = _registry()
    approved = log.approve("x_post", "ada")
    assert approved.get("approved") is True
    target = OmesPromptTarget(respond=registry_responder(registry))
    rows = run_battery(target, ['{"tool": "x_post", "arguments": {"text": "hi"}}'])
    payload = json.loads(rows[0]["response"])
    assert payload == {"posted": True, "text": "hi"}


def test_target_answers_are_assistant_messages():
    registry, _, _ = _registry()
    target = OmesPromptTarget(respond=registry_responder(registry))
    rows = run_battery(target, ['{"tool": "nope", "arguments": {}}'])
    assert "Unknown tool: nope" in rows[0]["response"]
    assert message_text(Message.from_prompt(prompt="a b", role="assistant")) == "a b"
