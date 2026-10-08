"""Flag the conversation loop reads at the start of each iteration.

Adapted from Hermes ``agent/interrupt_control.py``. Setting the flag stops the
loop before the next model call. It does not unwind a response already in hand.
"""

from __future__ import annotations

import threading


class InterruptFlag:
    """In-process interrupt. ``set`` from a tool or another thread; the loop polls ``is_set``."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self.message: str | None = None

    def set(self, message: str | None = None) -> None:
        with self._lock:
            if message is not None:
                self.message = message
            self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        with self._lock:
            self._event.clear()
            self.message = None


__all__ = ["InterruptFlag"]
