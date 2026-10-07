"""Text finish for one iteration: the model returned no tool call.

Adapted from Hermes ``agent/turn_final_response.py``. Append the assistant
message and stop the turn. Empty-response recovery, ack nudges, and stop gates
are not part of this phase. This function does not rebuild the system prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FinalResponseVerdict:
    """``action`` is ``break``: the turn has its answer."""

    action: str
    final_response: str | None = None
    turn_exit_reason: str | None = None


def finish_text_response(
    agent: Any,
    *,
    assistant_message: dict,
    messages: list,
    finish_reason: str = "stop",
) -> FinalResponseVerdict:
    """Append the assistant text and end the iteration. Do not rewrite earlier rows."""
    content = (
        assistant_message.get("content") if isinstance(assistant_message, dict) else ""
    )
    if content is None:
        content = ""
    elif not isinstance(content, str):
        content = str(content)
    messages.append({"role": "assistant", "content": content})
    return FinalResponseVerdict(
        action="break",
        final_response=content,
        turn_exit_reason=f"text_response(finish_reason={finish_reason})",
    )


__all__ = ["FinalResponseVerdict", "finish_text_response"]
