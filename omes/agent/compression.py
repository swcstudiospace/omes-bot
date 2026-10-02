"""The only rewrite of messages already appended to a turn.

Adapted from the Hermes compression entry the turn calls (``compress_after_tool_results``
and the conversation compressor). Older turns may be replaced with one summary.
The original system message, and the bytes of its content, stay as they are.
No auxiliary model call.
"""

from __future__ import annotations

from typing import Any

SUMMARY_KIND = "summary"
_SUMMARY_HEADING = "[CONTEXT SUMMARY]"


def compress_messages(messages: list) -> list:
    """Replace older turns with a summary. Leave the system prompt bytes unchanged.

    Short transcripts (nothing older than the kept tail) are returned as-is.
    The rewrite is in place so the caller's list object stays the transcript.
    """
    if not isinstance(messages, list) or len(messages) < 4:
        return messages
    system = None
    start = 0
    if isinstance(messages[0], dict) and messages[0].get("role") == "system":
        system = messages[0]
        start = 1
    body = list(messages[start:])
    if len(body) <= 2:
        return messages
    older = body[:-2]
    tail = body[-2:]
    summary = {
        "role": "user",
        "content": _summary_text(older),
        "display_kind": SUMMARY_KIND,
    }
    rewritten: list[Any] = []
    if system is not None:
        rewritten.append(system)
    rewritten.append(summary)
    rewritten.extend(tail)
    messages[:] = rewritten
    return messages


def _summary_text(older: list) -> str:
    lines = [_SUMMARY_HEADING]
    for message in older:
        if not isinstance(message, dict):
            lines.append(str(message))
            continue
        role = message.get("role", "?")
        content = message.get("content")
        text = content if isinstance(content, str) else ""
        calls = message.get("tool_calls") or []
        if calls:
            names = []
            for call in calls:
                function = call.get("function") if isinstance(call, dict) else None
                name = function.get("name") if isinstance(function, dict) else None
                if name:
                    names.append(str(name))
            text = (text + " " if text else "") + "tool calls: " + ", ".join(names)
        lines.append(f"{role}: {text[:200]}")
    return "\n".join(lines)


__all__ = ["SUMMARY_KIND", "compress_messages"]
