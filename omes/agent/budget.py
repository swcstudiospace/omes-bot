"""Iteration counter.

Adapted from Hermes ``agent/iteration_budget.py``. The counter only consumes or
refunds. The conversation loop refills the default budget it built from
``max_iterations`` at the start of each turn. A budget the caller supplied is a
session cap and is not refilled: when ``remaining`` hits 0 the loop stops, even
if the model asked for another tool. No grace call.
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

    def refill(self, max_total: int | None = None) -> None:
        """Restore a full cap. The loop calls this only for its default per-turn budget."""
        with self._lock:
            if max_total is not None:
                if max_total < 0:
                    raise ValueError(f"max_total must be >= 0, got {max_total}")
                self.max_total = max_total
            self._used = 0

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)


__all__ = ["IterationBudget"]
