"""Post-loop finalization. One result dict, no billing, no transcript hooks.

Adapted from Hermes ``agent/turn_finalizer.py``. A turn that falls out of the
loop on a tool row gets a visible assistant close so the next user message is
not ``tool → user``. That close is appended. Earlier rows are not rewritten.
There is no extra model call when the budget is spent.
"""

from __future__ import annotations

from typing import Any


def finalize_turn(
    agent: Any,
    *,
    final_response: str | None,
    messages: list,
    api_call_count: int,
    interrupted: bool,
    failed: bool,
    turn_exit_reason: str | None,
    task_id: str | None = None,
) -> dict:
    """Return the turn result. ``final_response`` and ``messages`` are always set."""
    reason = turn_exit_reason or "stopped"
    response = final_response
    if _stopped_on_tool_row(messages, response, interrupted):
        reason = reason if reason not in {None, "stopped"} else "pending_tool_result"
        response = (
            "No reply: the turn stopped while a tool result was still pending. "
            "The iteration budget or interrupt ended the loop before another model call."
        )
        messages.append({"role": "assistant", "content": response})
        if reason in {"stopped", "pending_tool_result"}:
            reason = "pending_tool_result"

    if response is None:
        response = ""

    budget_stop = reason == "budget_exhausted" or reason.startswith(
        "max_iterations_reached"
    )
    tool_stop = reason == "pending_tool_result"
    completed = (
        bool(response)
        and not failed
        and not interrupted
        and not budget_stop
        and not tool_stop
        and reason.startswith("text_response")
    )

    leftover = getattr(agent, "pending_steer", None)
    if leftover:
        agent.pending_steer = None

    interrupt = getattr(agent, "interrupt", None)
    interrupt_message = getattr(interrupt, "message", None) if interrupted else None
    if interrupt is not None and interrupted:
        interrupt.clear()

    result = {
        "final_response": response,
        "messages": messages,
        "api_calls": api_call_count,
        "completed": completed,
        "interrupted": interrupted,
        "failed": failed,
        "turn_exit_reason": reason,
    }
    if leftover:
        result["pending_steer"] = leftover
    if interrupt_message:
        result["interrupt_message"] = interrupt_message
    if task_id is not None:
        result["task_id"] = task_id
    return result


def _stopped_on_tool_row(
    messages: list, response: str | None, interrupted: bool
) -> bool:
    if interrupted or response:
        return False
    if not messages or not isinstance(messages[-1], dict):
        return False
    return messages[-1].get("role") == "tool"


__all__ = ["finalize_turn"]
