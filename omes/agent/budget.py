"""Per-turn iteration budget.

Adapted from Hermes ``agent/iteration_budget.py``. One counter for this agent.
When ``remaining`` hits 0 the loop stops, even if the model asked for another tool.
No grace call: a summary request would be another model call after the budget is spent.
"""

from __future__ import annotations

import threading


class IterationBudget:
    """Thread-safe consume/refund counter. ``consume`` fails closed at the cap."""

    def __init__(self, max_total: int):
        if max_total < 0:
            raise ValueError(f"max_total must be >= 0, got {max_total}")
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """Take one iteration. Return False when none remain."""
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        """Give one iteration back. Unused by this loop; kept so a later phase can."""
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)


__all__ = ["IterationBudget"]
