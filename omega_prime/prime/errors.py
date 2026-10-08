# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Structured errors for the Prime connector layer (CONN-01).

Every adapter failure is a :class:`PrimeError` with a machine-readable
``code`` and a human ``reason``; the wire shape is ``"code: reason"`` — the
same ``{"error": "code: reason"}`` surface the tool registry already returns.
"""

from __future__ import annotations


class PrimeError(Exception):
    """A typed connector-boundary failure."""

    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")

    def to_dict(self) -> dict:
        return {"error": str(self), "code": self.code, "reason": self.reason}


__all__ = ["PrimeError"]
