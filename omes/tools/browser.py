"""Browser navigate and snapshot through an injected transport.

Adapted from Hermes ``tools/browser_tool.py``. There is no browser process and
no socket. A missing transport is an error.
"""

from __future__ import annotations

from typing import Any


class BrowserSession:
    """Calls ``transport.navigate`` and ``transport.snapshot``. Does not connect."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def browser_navigate(self, url: str) -> dict[str, Any]:
        """Return ``{"url", "page"}`` from ``transport.navigate(url)``."""
        if self._transport is None:
            return {"error": "browser transport is not available"}
        if not isinstance(url, str) or url.strip() == "":
            return {"error": "url must be a non-empty string"}
        navigate = getattr(self._transport, "navigate", None)
        if not callable(navigate):
            return {"error": "browser transport has no navigate"}
        return {"url": url, "page": navigate(url)}

    def browser_snapshot(self) -> dict[str, Any]:
        """Return ``{"page"}`` from ``transport.snapshot()``."""
        if self._transport is None:
            return {"error": "browser transport is not available"}
        snapshot = getattr(self._transport, "snapshot", None)
        if not callable(snapshot):
            return {"error": "browser transport has no snapshot"}
        return {"page": snapshot()}


__all__ = ["BrowserSession"]
