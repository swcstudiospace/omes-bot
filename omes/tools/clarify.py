"""Record a question and return it.

Adapted from Hermes ``tools/clarify_tool.py``. This port does not open a UI.
It appends the question it was given and returns that question.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClarifyLog:
    """Questions recorded for one registration of the clarify tool."""

    questions: list[str] = field(default_factory=list)


def clarify(log: ClarifyLog, question: str) -> dict[str, Any]:
    """Append ``question`` to ``log`` and return it unchanged."""
    if not isinstance(question, str):
        return {"error": "question must be a string"}
    log.questions.append(question)
    return {"question": question}


__all__ = ["ClarifyLog", "clarify"]
