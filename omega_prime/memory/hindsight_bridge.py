"""Hindsight with a local fallback: service first, bank file when down.

``HindsightBridge`` keeps the local ``Hindsight`` call shapes
(retain/retain_batch/recall) while the service is primary: every call tries
the shared bank, and only a ``HindsightError`` drops to the local bank.
Reflect and page search have no local equivalent, so they degrade to empty.
"""

from __future__ import annotations

from typing import Any

from omega_prime.memory.hindsight_service import HindsightError


class HindsightBridge:
    """Service-first episodic memory with local fallback."""

    def __init__(self, service: Any, local: Any) -> None:
        self.service = service
        self.local = local

    def retain(self, content: str) -> dict:
        """Keep one entry: shared bank first, local bank when the service fails."""
        if not isinstance(content, str) or content.strip() == "":
            return {"ok": False, "reason": "content must be a non-empty string"}
        try:
            return self.service.retain([content])
        except HindsightError:
            return self.local.retain(content)

    def retain_batch(self, items: list[str]) -> dict:
        """Keep each non-blank item. Blanks are skipped, not errors."""
        if not isinstance(items, list):
            return {"ok": False, "reason": "items must be a list of strings"}
        strings = [item for item in items if isinstance(item, str)]
        try:
            return self.service.retain(strings)
        except HindsightError:
            return self.local.retain_batch(items)

    def recall(self, query: str, *, limit: int = 5) -> list[str]:
        """Shared-bank recall, or local-bank recall when the service fails."""
        try:
            return self.service.recall(query, limit=limit)
        except HindsightError:
            return self.local.recall(query, limit=limit)

    def reflect(self, query: str) -> str:
        """Shared-bank synthesis, or ``""`` when the service fails."""
        try:
            return self.service.reflect(query)
        except HindsightError:
            return ""

    def search_pages(self, query: str, *, limit: int = 3) -> list[dict]:
        """Shared-bank page hits, or ``[]`` when the service fails."""
        try:
            return self.service.search_pages(query, limit=limit)
        except HindsightError:
            return []


__all__ = ["HindsightBridge"]
