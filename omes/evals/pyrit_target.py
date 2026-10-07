"""Omes as a PyRIT target: adversarial prompts against the real registry.

`OmesPromptTarget` wraps a sync `respond(text) -> str` callable so PyRIT
orchestrators and scorers can drive it. The shipped responder,
`registry_responder`, parses `{"tool", "arguments"}` and returns
`registry.dispatch` verbatim — policy, approval, and unknown-tool refusals
included. Anything else returns a JSON error and dispatches nothing, so
injected text can never self-execute. Memory is in-memory SQLite: keyless
and fileless.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from pyrit.memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.models.messages.message import Message
from pyrit.prompt_target import PromptTarget


def ensure_memory() -> None:
    """Set an in-memory PyRIT memory once; reuse it afterwards."""
    try:
        CentralMemory.get_memory_instance()
    except ValueError:
        CentralMemory.set_memory_instance(SQLiteMemory(db_path=":memory:", silent=True))


class OmesPromptTarget(PromptTarget):
    """A PyRIT target whose answers come from `respond(text)`."""

    def __init__(self, *, respond: Callable[[str], str]) -> None:
        ensure_memory()
        super().__init__()
        self._respond = respond

    async def _send_prompt_to_target_async(
        self, *, normalized_conversation: list[Message]
    ) -> list[Message]:
        prompt = " ".join(
            piece.converted_value
            for message in normalized_conversation
            for piece in message.message_pieces
            if piece.converted_value
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


__all__ = [
    "OmesPromptTarget",
    "ensure_memory",
    "message_text",
    "registry_responder",
    "run_battery",
]
