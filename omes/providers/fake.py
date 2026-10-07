"""Scripted transport for provider tests. Records every call, sends nothing."""

from __future__ import annotations

from typing import Any

from omes.providers.base import ProviderError


class FakeTransport:
    """Replay scripted payloads. ``post_fn`` overrides the script per call."""

    def __init__(self, script: list[dict] | None = None, post_fn: Any = None) -> None:
        self.script = list(script) if script else []
        self.post_fn = post_fn
        self.calls: list[tuple[str, str, dict, dict]] = []

    def post(self, url: str, headers: dict, body: dict) -> dict:
        self.calls.append(("POST", url, dict(headers), body))
        if self.post_fn is not None:
            return self.post_fn(url, headers, body)
        if not self.script:
            raise ProviderError("fake transport script is empty")
        return self.script.pop(0)

    def get(self, url: str, headers: dict, params: dict) -> dict:
        self.calls.append(("GET", url, dict(headers), dict(params or {})))
        if self.post_fn is not None:
            return self.post_fn(url, headers, params)
        if not self.script:
            raise ProviderError("fake transport script is empty")
        return self.script.pop(0)


__all__ = ["FakeTransport"]
