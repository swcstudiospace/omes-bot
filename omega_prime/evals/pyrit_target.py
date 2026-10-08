"""Omega Prime as a PyRIT target: adversarial prompts against the real registry.

`OmegaPrimePromptTarget` wraps a sync `respond(text) -> str` callable so PyRIT
executors and scorers can drive it. The shipped responder,
`registry_responder`, parses `{"tool", "arguments"}` and returns
`registry.dispatch` verbatim — policy, approval, and unknown-tool refusals
included. Anything else returns a JSON error and dispatches nothing, so
injected text can never self-execute. Memory is in-memory SQLite: keyless
and fileless.

Multi-turn campaigns run through `MultiPromptSendingAttack` and are judged
per turn with case-sensitive `SubStringScorer`s. The target answers the
latest turn (single-prompt behavior is unchanged); registry state such as
approvals persists across turns, so campaigns can chain allow-then-act
sequences.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from pyrit.analytics.text_matching import ExactTextMatching
from pyrit.executor.attack.core.attack_config import AttackScoringConfig
from pyrit.executor.attack.multi_turn.multi_prompt_sending import (
    MultiPromptSendingAttack,
)
from pyrit.memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.models.messages.message import Message
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
from pyrit.prompt_target.common.target_configuration import TargetConfiguration
from pyrit.score.true_false.substring_scorer import SubStringScorer


def ensure_memory() -> None:
    """Set an in-memory PyRIT memory once; reuse it afterwards."""
    try:
        CentralMemory.get_memory_instance()
    except ValueError:
        CentralMemory.set_memory_instance(SQLiteMemory(db_path=":memory:", silent=True))


def _case_sensitive(substring: str) -> SubStringScorer:
    """Substring scorer matching battery semantics (exact case)."""
    return SubStringScorer(
        substring=substring, text_matcher=ExactTextMatching(case_sensitive=True)
    )


class OmegaPrimePromptTarget(PromptTarget):
    """A PyRIT target whose answers come from `respond(text)`.

    Declares native multi-turn support and answers the latest turn, so
    each campaign turn dispatches independently while registry state
    (approvals, policy) persists across the conversation.
    """

    def __init__(self, *, respond: Callable[[str], str]) -> None:
        ensure_memory()
        super().__init__(
            custom_configuration=TargetConfiguration(
                capabilities=TargetCapabilities(supports_multi_turn=True)
            )
        )
        self._respond = respond

    async def _send_prompt_to_target_async(
        self, *, normalized_conversation: list[Message]
    ) -> list[Message]:
        latest = normalized_conversation[-1] if normalized_conversation else None
        pieces = latest.message_pieces if latest is not None else []
        prompt = " ".join(
            piece.converted_value for piece in pieces if piece.converted_value
        )
        return [Message.from_prompt(prompt=self._respond(prompt), role="assistant")]


def registry_responder(registry: Any) -> Callable[[str], str]:
    """Return `respond` dispatching `{"tool", "arguments"}` JSON prompts."""

    def respond(text: str) -> str:
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "prompt is not a tool-dispatch object"})
        if not isinstance(payload, dict) or not isinstance(payload.get("tool"), str):
            return json.dumps({"error": "prompt needs a string tool name"})
        return registry.dispatch(payload["tool"], payload.get("arguments", {}))

    return respond


def message_text(message: Message) -> str:
    """Join the converted text of every piece."""
    return " ".join(
        piece.converted_value
        for piece in message.message_pieces
        if piece.converted_value
    )


def run_battery(target: PromptTarget, prompts: list[str]) -> list[dict[str, str]]:
    """Drive `send_prompt_async` per prompt in order. Return prompt/response rows."""

    async def _run() -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for prompt in prompts:
            answers = await target.send_prompt_async(
                message=Message.from_prompt(prompt=prompt, role="user")
            )
            rows.append(
                {
                    "prompt": prompt,
                    "response": " ".join(message_text(a) for a in answers),
                }
            )
        return rows

    return asyncio.run(_run())


def run_campaign(
    target: PromptTarget,
    objective: str,
    turns: list[dict[str, Any]],
    objective_substring: str | None = None,
) -> dict[str, Any]:
    """Run one multi-turn attack and judge every turn with scorers.

    Each turn is `{"prompt", "must_contain"?, "must_not_contain"?}`. Turns
    execute in one PyRIT conversation through `MultiPromptSendingAttack`;
    each response is judged with case-sensitive substring scorers. Returns
    `{"objective", "outcome", "turns", "verdict"}` where `verdict` is true
    only when every check matches. Keyless and deterministic.
    """
    if not turns:
        raise ValueError("run_campaign needs at least one turn")
    ensure_memory()
    config = None
    if objective_substring is not None:
        config = AttackScoringConfig(
            objective_scorer=_case_sensitive(objective_substring)
        )
    attack = MultiPromptSendingAttack(
        objective_target=target, attack_scoring_config=config
    )

    async def _run() -> dict[str, Any]:
        result = await attack.execute_async(
            objective=objective,
            user_messages=[
                Message.from_prompt(prompt=str(turn["prompt"]), role="user")
                for turn in turns
            ],
        )
        memory = CentralMemory.get_memory_instance()
        texts = [
            message_text(message)
            for message in memory.get_conversation_messages(
                conversation_id=result.conversation_id
            )
        ]
        responses = [texts[index] for index in range(1, len(texts), 2)]
        rows: list[dict[str, Any]] = []
        for turn, response in zip(turns, responses, strict=False):
            checks = await _judge_turn(
                response,
                [str(text) for text in turn.get("must_contain", [])],
                [str(text) for text in turn.get("must_not_contain", [])],
            )
            rows.append(
                {"prompt": turn["prompt"], "response": response, "checks": checks}
            )
        for turn in turns[len(rows) :]:
            rows.append({"prompt": turn["prompt"], "response": "", "checks": []})
        complete = len(responses) >= len(turns)
        verdict = complete and all(
            check["actual"] is check["expected"]
            for row in rows
            for check in row["checks"]
        )
        outcome = getattr(result.outcome, "name", str(result.outcome))
        return {
            "objective": objective,
            "outcome": outcome,
            "turns": rows,
            "verdict": verdict,
        }

    return asyncio.run(_run())


async def _judge_turn(
    response: str, must_contain: list[str], must_not_contain: list[str]
) -> list[dict[str, Any]]:
    """Score one response. Each check is `{substring, expected, actual}`."""
    message = Message.from_prompt(prompt=response, role="assistant")
    checks: list[dict[str, Any]] = []
    for substring in must_contain:
        scores = await _case_sensitive(substring).score_async(message)
        checks.append(
            {"substring": substring, "expected": True, "actual": _value(scores)}
        )
    for substring in must_not_contain:
        scores = await _case_sensitive(substring).score_async(message)
        checks.append(
            {"substring": substring, "expected": False, "actual": _value(scores)}
        )
    return checks


def _value(scores: Any) -> bool:
    """First score's boolean value. Missing scores read False."""
    if not scores:
        return False
    value = scores[0].get_value()
    return value is True


__all__ = [
    "OmegaPrimePromptTarget",
    "ensure_memory",
    "message_text",
    "registry_responder",
    "run_battery",
    "run_campaign",
]
