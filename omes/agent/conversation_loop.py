"""One conversation turn: interrupt, budget, one model call, tool round or text, finalize.

Adapted from Hermes ``agent/conversation_loop.py`` (``run_conversation`` and the
iteration in ``_run_conversation_turn``) and ``agent/turn_iteration_prep.py``.
The system prompt is installed once, before the loop, and is not rebuilt after
a tool round. Messages already appended are not rewritten here; compression is
the only sanctioned rewrite, and this loop does not call it.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from dataclasses import dataclass
from typing import Any

from omes.agent.budget import IterationBudget
from omes.agent.harness import (
    account_output,
    apply_tool_marks,
    drain_steer,
    emit,
    prepare_speculative,
    restore_tools,
    run_before_model,
    take_leftover_steer,
    wrap_tools,
)
from omes.agent.interrupt import InterruptFlag
from omes.agent.magic_keywords import notices_for_turn
from omes.agent.model import Model
from omes.agent.modes import apply_plan_mode
from omes.agent.prompt_builder import build_system_prompt, steer_user_row
from omes.agent.session_lease import SessionLease
from omes.agent.turn_final_response import FinalResponseVerdict, finish_text_response
from omes.agent.turn_finalizer import finalize_turn
from omes.agent.turn_tool_round import ToolRoundVerdict, run_tool_round


@dataclass
class Agent:
    """What the loop reads. Not ``AIAgent``: no credential, gateway, or callback parameters.

    ``tools`` is a name → callable map. ``interrupt`` is polled at the start of each
    iteration. ``pending_steer`` is delivered as its own user row after a tool result.
    ``lease`` is held for the turn. A budget the caller omits is per-turn and refilled
    from ``max_iterations``. A budget the caller passes is a session cap and is not reset.

    Omp harness options (all ``None`` by default, keeping the Hermes turn): ``before_model``
    may mutate the outgoing request or stop the turn before it is billed; ``pause_gate``
    parks the loop at both action boundaries; ``output_budget`` caps model-visible
    output chars; ``speculative_tools`` names discard-safe tools to pre-execute.

    Omp mode options: ``plan_mode`` refuses write tools without calling them;
    ``extensions`` is an :class:`ExtensionHooks` whose ``before_model`` hooks run
    before the legacy ``before_model`` hook each iteration.

    Durability options: ``journal`` is a :class:`TurnJournal` that persists
    every appended row; ``run_id`` names the run (a fresh hex id by default).

    Observability: ``tracer`` is a :class:`Tracer` recording one span per
    model call.

    Magic keywords: ``magic_keywords`` is a
    :class:`MagicKeywordSettings` (all on when omitted). A user turn
    containing ``ultrathink``, ``orchestrate``, or ``workflowz`` as
    standalone prose gains that word's notice rows for the turn.

    Substrate surface: ``substrate`` is a :class:`SubstrateSession` (or
    duck-typed equivalent). Each turn opens it once (brief cached after the
    first open), prepends its brief block to the system prompt, and emits
    the prompt plus a turn-end note. Tool calls are reported from the tool
    round. ``None`` keeps the turn fully local.
    """

    model: Model
    tools: dict[str, Any] | None = None
    max_iterations: int = 90
    budget: IterationBudget | None = None
    interrupt: InterruptFlag | None = None
    pending_steer: str | None = None
    lease: SessionLease | None = None
    before_model: Any | None = None
    pause_gate: Any | None = None
    output_budget: Any | None = None
    speculative_tools: Any | None = None
    plan_mode: bool = False
    extensions: Any | None = None
    journal: Any | None = None
    run_id: str | None = None
    tracer: Any | None = None
    magic_keywords: Any | None = None
    substrate: Any | None = None
    delegate_depth: int = 0
    max_depth: int = 2
    max_children: int = 1
    child_model: Any | None = None
    child_tool_hook: Any | None = None
    _cached_system_prompt: str | None = None
    _turn_budget: IterationBudget | None = None

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
        system_message = _open_substrate(agent, user_message, system_message)
        result = _run_conversation_turn(
            agent,
            user_message,
            system_message=system_message,
            conversation_history=conversation_history,
            task_id=task_id,
        )
        _close_substrate_turn(agent, result)
        return result
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
    emit(agent, "turn_start")
    run_id = _begin_journal(agent)
    since = len(messages)
    _install_system_prompt(agent, messages, system_message)
    messages.append({"role": "user", "content": user_message})
    if isinstance(user_message, str):
        messages.extend(
            notices_for_turn(user_message, agent.tools, agent.magic_keywords)
        )
    _emit_new_rows(agent, messages, since)
    _journal_new_rows(agent, run_id, messages, since)

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
        assert budget is not None
        budget.refill(agent.max_iterations)

    original_tools = wrap_tools(agent)
    if agent.plan_mode:
        assert agent.tools is not None
        agent.tools = apply_plan_mode(agent.tools)
    try:
        while api_call_count < agent.max_iterations and budget.remaining > 0:
            if agent.pause_gate is not None and not agent.pause_gate.wait_until_resumed(
                agent.interrupt
            ):
                interrupted = True
                turn_exit_reason = "interrupted_by_user"
                break
            if agent.interrupt is not None and agent.interrupt.is_set():
                interrupted = True
                turn_exit_reason = "interrupted_by_user"
                break
            stop = _run_extension_hooks(agent, messages)
            if stop is None:
                stop = run_before_model(agent, messages, agent.tools)
            if stop is not None:
                turn_exit_reason = str(stop.get("reason", "stopped_before_model"))
                break
            if not budget.consume():
                turn_exit_reason = "budget_exhausted"
                break
            api_call_count += 1
            started = time.monotonic()
            assistant_message = agent.model.complete(messages, original_tools)
            _trace_model_call(agent, started)
            if not isinstance(assistant_message, dict):
                raise TypeError("model.complete must return an assistant message dict")
            if not account_output(agent, assistant_message.get("content")):
                turn_exit_reason = "output_budget_exceeded"
                break
            if _tool_calls(assistant_message):
                _fold_queued_steer(agent)
                since = len(messages)
                if agent.speculative_tools and not agent.plan_mode:
                    prepare_speculative(
                        agent, original_tools, _tool_calls(assistant_message)
                    )
                verdict: ToolRoundVerdict | FinalResponseVerdict = run_tool_round(
                    agent,
                    assistant_message=assistant_message,
                    messages=messages,
                    task_id=task_id,
                )
                late_steer = drain_steer(agent)
                if late_steer:
                    messages.append(steer_user_row(late_steer))
                apply_tool_marks(agent, messages, since)
                _emit_new_rows(agent, messages, since)
                _journal_new_rows(agent, run_id, messages, since)
                if not account_output(
                    agent, *[_tool_content(row) for row in messages[since:]]
                ):
                    turn_exit_reason = "output_budget_exceeded"
                    break
                if verdict.action == "break":
                    final_response = verdict.final_response
                    turn_exit_reason = verdict.turn_exit_reason
                    break
                continue
            finish_reason = assistant_message.get("finish_reason") or "stop"
            since = len(messages)
            verdict = finish_text_response(
                agent,
                assistant_message=assistant_message,
                messages=messages,
                finish_reason=str(finish_reason),
            )
            _emit_new_rows(agent, messages, since)
            _journal_new_rows(agent, run_id, messages, since)
            final_response = verdict.final_response
            turn_exit_reason = verdict.turn_exit_reason
            break

        if turn_exit_reason is None:
            if api_call_count >= agent.max_iterations:
                turn_exit_reason = (
                    f"max_iterations_reached({api_call_count}/{agent.max_iterations})"
                )
            elif budget.remaining <= 0:
                turn_exit_reason = "budget_exhausted"
            else:
                turn_exit_reason = "stopped"

        _report_leftover_steer(agent)
        since = len(messages)
        result = finalize_turn(
            agent,
            final_response=final_response,
            messages=messages,
            api_call_count=api_call_count,
            interrupted=interrupted,
            failed=failed,
            turn_exit_reason=turn_exit_reason,
            task_id=task_id,
        )
        _emit_new_rows(agent, messages, since)
        _journal_new_rows(agent, run_id, messages, since)
        emit(agent, "turn_end", turn_exit_reason=result["turn_exit_reason"])
        _finish_journal(agent, run_id, result)
        return result
    finally:
        restore_tools(agent, original_tools)


def _open_substrate(
    agent: Agent, user_message: Any, system_message: str | None
) -> str | None:
    """Open the substrate session; prepend its brief block. Never raises."""
    substrate = getattr(agent, "substrate", None)
    if substrate is None:
        return system_message
    try:
        substrate.open()
        block = substrate.brief_block()
    except Exception:
        return system_message
    if block:
        system_message = f"{block}\n\n{system_message}" if system_message else block
    with contextlib.suppress(Exception):
        substrate.on_prompt(user_message)
    return system_message


def _close_substrate_turn(agent: Agent, result: dict) -> None:
    """Report the turn-end note. Never raises."""
    substrate = getattr(agent, "substrate", None)
    if substrate is None:
        return
    try:
        reason = result.get("turn_exit_reason") if isinstance(result, dict) else None
        substrate.on_turn_end(reason)
    except Exception:
        pass


def _install_system_prompt(
    agent: Agent, messages: list, system_message: str | None
) -> None:
    """Build the system prompt once. A history that already starts with one is reused."""
    if (
        messages
        and isinstance(messages[0], dict)
        and messages[0].get("role") == "system"
    ):
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


def _trace_model_call(agent: Agent, started: float) -> None:
    """Record one model span. No tracer, no-op."""
    tracer = getattr(agent, "tracer", None)
    if tracer is None:
        return
    elapsed_ms = round((time.monotonic() - started) * 1000.0, 3)
    fields: dict[str, Any] = {"model": type(agent.model).__name__}
    usage = getattr(agent.model, "last_usage", None)
    if isinstance(usage, dict) and usage:
        counters = {
            key: value
            for key, value in usage.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        if counters:
            fields["usage"] = counters
    tracer.span(
        "model",
        type(agent.model).__name__,
        fields,
        duration_ms=max(0.0, elapsed_ms),
    )


def _begin_journal(agent: Agent) -> str | None:
    """Open the journal run. None when the agent journals nothing."""
    journal = getattr(agent, "journal", None)
    if journal is None:
        return None
    run_id = getattr(agent, "run_id", None)
    if not run_id:
        run_id = uuid.uuid4().hex
        agent.run_id = run_id
    journal.begin_run(run_id)
    return run_id


def _journal_new_rows(
    agent: Agent, run_id: str | None, messages: list, since: int
) -> None:
    """Persist rows appended at ``messages[since:]``. No journal, no-op."""
    journal = getattr(agent, "journal", None)
    if journal is None or run_id is None:
        return
    for row in messages[since:]:
        journal.append(run_id, dict(row) if isinstance(row, dict) else {"row": row})


def _finish_journal(agent: Agent, run_id: str | None, result: dict) -> None:
    """Close the journal run with the result's reason and response."""
    journal = getattr(agent, "journal", None)
    if journal is None or run_id is None:
        return
    response = result.get("final_response", "")
    journal.finish_run(
        run_id, str(result.get("turn_exit_reason", "stopped")), str(response)
    )


def _run_extension_hooks(agent: Agent, messages: list) -> dict | None:
    """Run registered extension hooks; None when none stop the turn."""
    extensions = getattr(agent, "extensions", None)
    if extensions is None:
        return None
    return extensions.run_before_model(messages, agent.tools)


def _tool_calls(message: dict) -> list:
    calls = message.get("tool_calls")
    return calls if isinstance(calls, list) and calls else []


def _emit_new_rows(agent: Agent, messages: list, since: int) -> None:
    """Emit one ``message`` event per row appended at ``messages[since:]``."""
    for row in messages[since:]:
        role = row.get("role") if isinstance(row, dict) else None
        emit(agent, "message", role=role)


def _tool_content(row: Any) -> str:
    if isinstance(row, dict) and row.get("role") == "tool":
        content = row.get("content", "")
        return content if isinstance(content, str) else str(content)
    return ""


def _fold_queued_steer(agent: Agent) -> None:
    """Fold harness-queued steer into the legacy slot for the tool round."""
    if getattr(agent, "_steer_queue", None):
        agent.pending_steer = drain_steer(agent)


def _report_leftover_steer(agent: Agent) -> None:
    """Move undelivered queued steer onto the legacy slot for the finalizer."""
    leftover = take_leftover_steer(agent)
    if leftover:
        queued = "\n".join(part for part in leftover if part.strip())
        legacy = agent.pending_steer
        if legacy:
            queued = f"{queued}\n{legacy}" if queued else str(legacy)
        agent.pending_steer = queued or None


__all__ = ["Agent", "run_conversation"]
