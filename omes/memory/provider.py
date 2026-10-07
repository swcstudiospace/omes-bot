"""Memory provider surface. Prefetch skips greetings and slash commands.

The trivial-prompt list matches Hermes: empty text, slash commands, and the
greeting and acknowledgement words, with trailing punctuation allowed.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from omes.credentials.redact import redact_text
from omes.memory.store import MemoryStore

INDICATOR_GLYPH = "🧠"

# Anchored, then only whitespace or punctuation, so "k8s" and "note" do not match.
TRIVIAL_PROMPT_RE = re.compile(
    r"^(yes|no|ok|okay|sure|thanks|thank you|y|n|yep|nope|yeah|nah|"
    r"hi|hey|hello|yo|sup|"
    r"continue|go ahead|do it|proceed|got it|cool|nice|great|done|next|lgtm|k)"
    r"""[\s!?.:;,"'~\u2018\u2019\u201c\u201d\u2014\u2013\u2026()\[\]{}<>*&^%$#@!+=`\u00a0]*$""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RecallStatus:
    """What the last prefetch injected. ``count == 0`` means content without a count."""

    provider_label: str
    count: int
    glyph: str = INDICATOR_GLYPH


def is_trivial_prompt(text: str | None) -> bool:
    """True for empty input, slash commands, and bare greetings or acknowledgements."""
    stripped = (text or "").strip()
    if not stripped or stripped.startswith("/"):
        return True
    return bool(TRIVIAL_PROMPT_RE.match(stripped))


class MemoryProvider(ABC):
    """Pluggable recall. ``prefetch`` returns ``""`` unless a subclass overrides it."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, for example ``builtin``."""

    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider can serve a turn."""

    @abstractmethod
    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Bind session state once at startup."""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Formatted recall for the upcoming turn. The default is no recall."""
        return ""

    @abstractmethod
    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """OpenAI-style tool schemas this provider handles."""

    @abstractmethod
    def handle_tool_call(
        self, tool_name: str, args: dict[str, Any], **kwargs: Any
    ) -> str:
        """Handle one tool call. Must return a JSON string."""


class BuiltinMemoryProvider(MemoryProvider):
    """Recall and writes go through one ``MemoryStore``."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self._session_id = ""

    @property
    def name(self) -> str:
        return "builtin"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self._session_id = session_id
        self.store.load_from_disk()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if is_trivial_prompt(
            query if isinstance(query, str) or query is None else None
        ):
            return ""
        self.store.load_from_disk()
        return redact_text(self.store.render())

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "memory",
                "description": (
                    "Add, replace, or remove one entry in MEMORY.md or USER.md. "
                    "Entries are joined by a section delimiter."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "replace", "remove"],
                        },
                        "target": {"type": "string", "enum": ["memory", "user"]},
                        "content": {"type": "string"},
                        "old_text": {"type": "string"},
                    },
                    "required": ["action"],
                },
            }
        ]

    def handle_tool_call(
        self, tool_name: str, args: dict[str, Any], **kwargs: Any
    ) -> str:
        if tool_name != "memory":
            return json.dumps(
                {
                    "success": False,
                    "error": f"Provider builtin does not handle tool '{tool_name}'.",
                },
                ensure_ascii=False,
            )
        payload = args or {}
        action = payload.get("action")
        target = payload.get("target") or "memory"
        content = payload.get("content")
        if content is None:
            content = payload.get("new_text")
        old_text = payload.get("old_text")
        if action == "add":
            result = self.store.add(target, "" if content is None else content)
        elif action == "replace":
            result = self.store.replace(
                target,
                "" if old_text is None else old_text,
                "" if content is None else content,
            )
        elif action == "remove":
            result = self.store.remove(target, "" if old_text is None else old_text)
        else:
            result = {
                "success": False,
                "error": f"Unknown action '{action}'. Use add, replace, or remove.",
            }
        return json.dumps(result, ensure_ascii=False)


__all__ = [
    "BuiltinMemoryProvider",
    "MemoryProvider",
    "RecallStatus",
    "is_trivial_prompt",
]
