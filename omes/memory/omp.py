"""Omp memory call shape over the phase 4 store.

Ports the ``MEMORY_BACKEND_TOOL_NAMES`` verbs (``retain``, ``recall``,
``memory_edit``, plus ``forget``) from
``packages/coding-agent/src/memory-backend/tool-names.ts`` as a thin adapter:
writes delegate to ``MemoryStore.add``/``replace``/``remove``, and recall is
a deterministic case-insensitive substring match — no embeddings, no
reranking, no model call. Nothing here touches the filesystem except through
the store it was given.
"""

from __future__ import annotations

from typing import Any

from omes.memory.store import MemoryStore


class OmpMemory:
    """``retain``/``recall``/``edit``/``forget`` on one ``MemoryStore``."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def retain(self, content: str, *, target: str = "memory") -> dict:
        """Append one entry. Blank content is refused without a store call."""
        if not isinstance(content, str) or content.strip() == "":
            return {"ok": False, "reason": "content must be a non-empty string"}
        return _ok(self.store.add(target, content))

    def recall(self, query: str, *, limit: int = 5) -> list[str]:
        """Entries containing ``query``, memory target first, stable order."""
        _check_limit(limit)
        if not isinstance(query, str) or query == "":
            return []
        needle = query.lower()
        found: list[str] = []
        for entries in (self.store.memory_entries, self.store.user_entries):
            for entry in entries:
                if needle in entry.lower():
                    found.append(entry)
                    if len(found) >= limit:
                        return found
        return found

    def edit(self, old_text: str, new_content: str, *, target: str = "memory") -> dict:
        """Replace the entry holding ``old_text``."""
        return _ok(self.store.replace(target, old_text, new_content))

    def forget(self, old_text: str, *, target: str = "memory") -> dict:
        """Remove the entry holding ``old_text``."""
        return _ok(self.store.remove(target, old_text))


def _check_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")


def _ok(result: dict[str, Any]) -> dict:
    if result.get("success"):
        return {"ok": True}
    reason = result.get("error", "store refused the write")
    return {"ok": False, "reason": str(reason)}


__all__ = ["OmpMemory"]
