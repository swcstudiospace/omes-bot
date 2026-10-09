# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Compare the default-off public loop against executed pre-v10 transcripts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.harness import events_of
from omega_prime.agent.model import ScriptedModel
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.registry import ToolRegistry

FIXTURE = json.loads(
    (Path(__file__).parent / "parity" / "pre_v10_loop_transcript.json").read_text()
)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["id"])
def test_default_off_consumer_matches_executed_pre_v10_transcript(case):
    counter = [0]

    def advance_counter(amount):
        counter[0] += amount
        return {"total": counter[0]}

    def fail_operation():
        raise ValueError("historical operation failed")

    approvals = ApprovalLog()
    if case["approved"]:
        approvals.approve("advance_counter", "historical-human")
    registry = ToolRegistry(approval_log=approvals)
    registry.register(
        "advance_counter",
        "Advance a stateful counter",
        {
            "type": "object",
            "properties": {"amount": {"type": "integer"}},
            "required": ["amount"],
        },
        advance_counter,
        requires_approval=True,
    )
    registry.register(
        "fail_operation",
        "Report a deterministic operation failure",
        {"type": "object", "properties": {}},
        fail_operation,
    )

    def dispatcher(name):
        def dispatch(**arguments):
            return registry.dispatch(name, arguments)

        return dispatch

    tools = {
        row["function"]["name"]: dispatcher(row["function"]["name"])
        for row in registry.schemas()
    }
    model = ScriptedModel(case["script"])
    agent = Agent(model=model, tools=tools, max_iterations=case["max_iterations"])
    result = run_conversation(agent, case["user_message"], task_id=case["id"])
    observed = {
        "result": result,
        "model_requests": model.seen,
        "offered_tools": [sorted(offered) for offered in model.tools_seen],
        "events": events_of(agent),
        "counter": counter[0],
        "approved": approvals.is_approved("advance_counter"),
        "model_call_count": model.call_count,
        "model_remaining": model.remaining,
    }
    assert observed == case["expected"]
