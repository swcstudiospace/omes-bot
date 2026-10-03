"""Mnemopi call shape over the phase 4 store.

Ports ``remember``/``recall``/``get``/``forget`` from
``packages/mnemopi/src/core/memory.ts`` as id-tagged entries on the one
``MemoryStore``: each entry is stored as
``"[mnemopi:{bank}:{id}] {content}"`` on the ``memory`` target. Ids
(``mem-1``, ...) are assigned by scanning this bank's existing tags for the
max, so a new client on the same directory never reuses an id. Recall is a
deterministic substring match — no embeddings, no extraction, no model call.
"""

from __future__ import annotations

import re

from omes.memory.store import MemoryStore

_TAG = re.compile(r"^\[mnemopi:([^\[\]]+):(mem-\d+)\] (.*)$", re.DOTALL)


class Mnemopi:
    """Id-addressed remember and recall on one ``MemoryStore``."""

    def __init__(self, store: MemoryStore, bank: str = "default") -> None:
        _check_bank(bank)
        self.store = store
        self.bank = bank

    def remember(self, content: str) -> str:
        """Store one entry. Return its id."""
        if not isinstance(content, str) or content.strip() == "":
            raise ValueError("content must be a non-empty string")
        memory_id = self._next_id()
        result = self.store.add(
            "memory", f"[mnemopi:{self.bank}:{memory_id}] {content.strip()}"
        )
        if not result.get("success"):
            raise ValueError(str(result.get("error", "store refused the write")))
        return memory_id

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """This bank's entries matching ``query`` as ``{"id", "content"}``."""
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if not isinstance(query, str) or query == "":
            return []
        needle = query.lower()
        found: list[dict] = []
        for memory_id, content in self._bank_entries():
            if needle in content.lower():
                found.append({"id": memory_id, "content": content})
                if len(found) >= top_k:
                    break
        return found

    def get(self, memory_id: str) -> dict | None:
        """One entry by id, or None."""
        for candidate_id, content in self._bank_entries():
            if candidate_id == memory_id:
                return {"id": candidate_id, "content": content}
        return None

    def forget(self, memory_id: str) -> bool:
        """Remove one entry by id. True when one was removed."""
        prefix = f"[mnemopi:{self.bank}:{memory_id}] "
        for entry in list(self.store.memory_entries):
            if entry.startswith(prefix):
                result = self.store.remove("memory", entry)
                return bool(result.get("success"))
        return False

    def _bank_entries(self) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        for entry in self.store.memory_entries:
            match = _TAG.match(entry)
            if match is not None and match.group(1) == self.bank:
                entries.append((match.group(2), match.group(3)))
        return entries

    def _next_id(self) -> str:
        highest = 0
        for memory_id, _ in self._bank_entries():
            try:
                number = int(memory_id.split("-", 1)[1])
            except (IndexError, ValueError):
                continue
            highest = max(highest, number)
        return f"mem-{highest + 1}"


def _check_bank(bank: str) -> None:
    if (
        not isinstance(bank, str)
        or bank == ""
        or any(char.isspace() for char in bank)
        or "[" in bank
        or "]" in bank
    ):
        raise ValueError("bank must be a non-empty string without whitespace or brackets")


__all__ = ["Mnemopi"]
