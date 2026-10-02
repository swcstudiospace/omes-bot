"""Fan a turn's recall out to every registered provider.

``prefetch_all`` concatenates non-empty provider blocks. ``handle_tool_call``
for ``memory`` goes to the builtin provider.
"""

from __future__ import annotations

import json
from typing import Any

from omes.memory.provider import MemoryProvider


class MemoryManager:
    """Ordered list of providers. Registration order is recall order."""

    def __init__(self) -> None:
        self._providers: list[MemoryProvider] = []

    def add_provider(self, provider: MemoryProvider) -> None:
        self._providers.append(provider)

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """Join every provider's non-empty prefetch with a blank line."""
        parts: list[str] = []
        for provider in self._providers:
            block = provider.prefetch(query, session_id=session_id) or ""
            if block.strip():
                parts.append(block)
        return "\n\n".join(parts)

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        """Dispatch ``memory`` to the builtin provider. Other names are an error."""
        if tool_name != "memory":
            return json.dumps(
                {"success": False, "error": f"No memory provider handles tool '{tool_name}'."},
                ensure_ascii=False,
            )
        provider = next((item for item in self._providers if item.name == "builtin"), None)
        if provider is None:
            return json.dumps(
                {"success": False, "error": "No memory provider handles tool 'memory'."},
                ensure_ascii=False,
            )
        return provider.handle_tool_call(tool_name, args or {}, **kwargs)


__all__ = ["MemoryManager"]
