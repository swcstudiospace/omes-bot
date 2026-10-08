"""Flags-off regression (LOOP-07): with every Prime family flag at its default
(off), the loop and the default registry are bit-for-bit the pre-v10 behavior.
"""

from __future__ import annotations

from pathlib import Path

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.harness import events_of
from omega_prime.agent.model import ScriptedModel
from omega_prime.mcp_server import default_registry
from omega_prime.tools.agent_message import MESSAGING_TOOL_NAMES
from omega_prime.tools.autonomous import AUTONOMOUS_TOOL_NAMES
from omega_prime.tools.goals import GOAL_TOOL_NAMES
from omega_prime.tools.harness import HARNESS_TOOL_NAMES
from omega_prime.tools.heartbeat import HEARTBEAT_TOOL_NAMES
from omega_prime.tools.rlm import RLM_TOOL_NAMES

ROOT = Path(__file__).resolve().parents[2]

PRIME_TOOL_NAMES = (
    tuple(RLM_TOOL_NAMES)
    + tuple(HARNESS_TOOL_NAMES)
    + tuple(GOAL_TOOL_NAMES)
    + tuple(HEARTBEAT_TOOL_NAMES)
    + tuple(AUTONOMOUS_TOOL_NAMES)
    + tuple(MESSAGING_TOOL_NAMES)
)


def _tool_call(name: str, arguments: str = "{}", call_id: str = "call-1") -> dict:
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


def test_flags_off_loop_emits_no_prime_events():
    model = ScriptedModel(
        [
            _tool_call("echo"),
            {"role": "assistant", "content": "done"},
        ]
    )
    agent = Agent(model=model, tools={"echo": lambda: "pong"}, max_iterations=4)
    result = run_conversation(agent, "ping", system_message="sys")

    assert result["messages"][-1]["content"] == "done"
    prime_events = [
        event for event in events_of(agent) if event["type"].startswith("prime_")
    ]
    assert prime_events == []


def test_flags_off_default_registry_has_no_prime_tools(tmp_path):
    registry = default_registry(ROOT, tmp_path)
    names = {schema["function"]["name"] for schema in registry.schemas()}
    for prime_name in PRIME_TOOL_NAMES:
        assert prime_name not in names
