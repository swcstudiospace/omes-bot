"""In-process lease for one conversation turn.

Adapted from Hermes ``agent/turn_facade_lease.py`` without the database row, the
refresher, or the liveness watchdog. The turn acquires it on the way in and
releases it on the way out, including when the turn raises.
"""

from __future__ import annotations

import threading


class SessionLease:
    """One holder at a time. ``held`` is true only between ``acquire`` and ``release``."""

    def __init__(self) -> None:
        self._held = False
        self._lock = threading.Lock()

    @property
    def held(self) -> bool:
        with self._lock:
            return self._held

    def acquire(self) -> None:
        with self._lock:
            if self._held:
                raise RuntimeError("session lease already held")
            self._held = True

    def release(self) -> None:
        with self._lock:
            self._held = False

    def __enter__(self) -> SessionLease:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.release()
        return False


__all__ = ["SessionLease"]
