"""Hindsight call shape over the phase 4 store.

Ports ``retain``/``retainBatch``/``recall`` from
``packages/coding-agent/src/hindsight/client.ts`` as bank-tagged entries on
the one ``MemoryStore``: each entry is stored as
``"[hindsight:{bank}] {content}"`` on the ``memory`` target, so banks share
the file without ever matching each other's recalls. Recall strips the tag
and matches case-insensitively — no vector search, no model call.
"""

from __future__ import annotations

from omes.memory.store import MemoryStore


class Hindsight:
    """Bank-scoped retain and recall on one ``MemoryStore``."""

    def __init__(self, store: MemoryStore, bank: str = "default") -> None:
        _check_bank(bank)
        self.store = store
        self.bank = bank

    def retain(self, content: str) -> dict:
        """Keep one entry in this bank."""
        if not isinstance(content, str) or content.strip() == "":
            return {"ok": False, "reason": "content must be a non-empty string"}
        result = self.store.add("memory", f"[hindsight:{self.bank}] {content.strip()}")
        if result.get("success"):
            return {"ok": True}
        return {"ok": False, "reason": str(result.get("error", "store refused"))}

    def retain_batch(self, items: list[str]) -> dict:
        """Keep each non-blank item. Blanks are skipped, not errors."""
        if not isinstance(items, list):
            return {"ok": False, "reason": "items must be a list of strings"}
        kept = 0
        for item in items:
            if not isinstance(item, str) or item.strip() == "":
                continue
            result = self.retain(item)
            if result.get("ok"):
                kept += 1
            else:
                return {"ok": False, "reason": str(result.get("reason"))}
        return {"ok": True, "count": kept}

    def recall(self, query: str, *, limit: int = 5) -> list[str]:
        """This bank's entries matching ``query``, tags stripped."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not isinstance(query, str) or query == "":
            return []
        needle = query.lower()
        prefix = f"[hindsight:{self.bank}] "
        found: list[str] = []
        for entry in self.store.memory_entries:
            if not entry.startswith(prefix):
                continue
            content = entry[len(prefix) :]
            if needle in content.lower():
                found.append(content)
                if len(found) >= limit:
                    break
        return found


def _check_bank(bank: str) -> None:
    if (
        not isinstance(bank, str)
        or bank == ""
        or any(char.isspace() for char in bank)
        or "[" in bank
        or "]" in bank
    ):
        raise ValueError(
            "bank must be a non-empty string without whitespace or brackets"
        )


__all__ = ["Hindsight"]
