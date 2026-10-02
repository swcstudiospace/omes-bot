"""One conversation turn: interrupt, budget, one model call, tool round or text, finalize.

Adapted from Hermes ``agent/conversation_loop.py`` (``run_conversation`` and the
iteration in ``_run_conversation_turn``) and ``agent/turn_iteration_prep.py``.
The system prompt is installed once, before the loop, and is not rebuilt after
a tool round. Messages already appended are not rewritten here; compression is
the only sanctioned rewrite, and this loop does not call it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omes.agent.budget import IterationBudget
from omes.agent.interrupt import InterruptFlag
from omes.agent.model import Model
from omes.agent.prompt_builder import build_system_prompt
from omes.agent.session_lease import SessionLease
from omes.agent.turn_final_response import finish_text_response
from omes.agent.turn_finalizer import finalize_turn
from omes.agent.turn_tool_round import run_tool_round


@dataclass
class Agent:
    """What the loop reads. Not ``AIAgent``: no credential, gateway, or callback parameters.

    ``tools`` is a name → callable map. ``interrupt`` is polled at the start of each
    iteration. ``pending_steer`` is delivered as its own user row after a tool result.
    ``lease`` is held for the turn. A budget the caller omits is per-turn and refilled
    from ``max_iterations``. A budget the caller passes is a session cap and is not reset.
    """

    model: Model
    tools: dict[str, Any] | None = None
    max_iterations: int = 90
    budget: IterationBudget | None = None
    interrupt: InterruptFlag | None = None
    pending_steer: str | None = None
    lease: SessionLease | None = None

    def __post_init__(self) -> None:
        if self.tools is None:
            self.tools = {}
        # Only the budget this agent created is per-turn. A caller-supplied budget
        # stays a session cap so spending it still stops later turns.
        if self.budget is None:
            self.budget = IterationBudget(self.max_iterations)
            self._turn_budget = self.budget
        else:
            self._turn_budget = None
        if self.interrupt is None:
            self.interrupt = InterruptFlag()
        if self.lease is None:
            self.lease = SessionLease()


def run_conversation(
    agent: Agent,
    user_message: Any,
    system_message: str | None = None,
    conversation_history: list | None = None,
    task_id: str | None = None,
) -> dict:
    """Run one turn. Return ``final_response`` and ``messages``.

    The session lease is taken before the turn and released on the way out,
    including when the turn raises.
    """
    lease = agent.lease
    if lease is None:
        lease = SessionLease()
        agent.lease = lease
    lease.acquire()
    try:
        return _run_conversation_turn(
            agent,
            user_message,
            system_message=system_message,
            conversation_history=conversation_history,
            task_id=task_id,
        )
    finally:
        lease.release()


def _run_conversation_turn(
    agent: Agent,
    user_message: Any,
    *,
    system_message: str | None,
    conversation_history: list | None,
    task_id: str | None,
) -> dict:
    messages: list = conversation_history if conversation_history is not None else []
    _install_system_prompt(agent, messages, system_message)
    messages.append({"role": "user", "content": user_message})

    api_call_count = 0
    final_response: str | None = None
    interrupted = False
    failed = False
    turn_exit_reason: str | None = None
    budget = agent.budget
    if budget is None:
        budget = IterationBudget(agent.max_iterations)
        agent.budget = budget
        agent._turn_budget = budget
    elif budget is getattr(agent, "_turn_budget", None):
        budget.refill(agent.max_iterations)

    while api_call_count < agent.max_iterations and budget.remaining > 0:
        if agent.interrupt is not None and agent.interrupt.is_set():
            interrupted = True
            turn_exit_reason = "interrupted_by_user"
            break
        if not budget.consume():
            turn_exit_reason = "budget_exhausted"
            break
        api_call_count += 1
        assistant_message = agent.model.complete(messages, agent.tools)
        if not isinstance(assistant_message, dict):
            raise TypeError("model.complete must return an assistant message dict")
        if _tool_calls(assistant_message):
            verdict = run_tool_round(
                agent,
                assistant_message=assistant_message,
                messages=messages,
                task_id=task_id,
            )
            if verdict.action == "break":
                final_response = verdict.final_response
                turn_exit_reason = verdict.turn_exit_reason
                break
            continue
        finish_reason = assistant_message.get("finish_reason") or "stop"
        verdict = finish_text_response(
            agent,
            assistant_message=assistant_message,
            messages=messages,
            finish_reason=str(finish_reason),
        )
        final_response = verdict.final_response
        turn_exit_reason = verdict.turn_exit_reason
        break

    if turn_exit_reason is None:
        if api_call_count >= agent.max_iterations:
            turn_exit_reason = f"max_iterations_reached({api_call_count}/{agent.max_iterations})"
        elif budget.remaining <= 0:
            turn_exit_reason = "budget_exhausted"
        else:
            turn_exit_reason = "stopped"

    return finalize_turn(
        agent,
        final_response=final_response,
        messages=messages,
        api_call_count=api_call_count,
        interrupted=interrupted,
        failed=failed,
        turn_exit_reason=turn_exit_reason,
        task_id=task_id,
    )


def _install_system_prompt(agent: Agent, messages: list, system_message: str | None) -> None:
    """Build the system prompt once. A history that already starts with one is reused."""
    if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
        content = messages[0].get("content")
        if isinstance(content, str) and content:
            agent._cached_system_prompt = content
            return
    prompt = build_system_prompt(agent, system_message)
    row = {"role": "system", "content": prompt}
    if not messages:
        messages.append(row)
    else:
        messages.insert(0, row)


def _tool_calls(message: dict) -> list:
    calls = message.get("tool_calls")
    return calls if isinstance(calls, list) and calls else []


__all__ = ["Agent", "run_conversation"]
