"""Provider contract feeding real models into the turn loop.

Ports the declarative Hermes ``ProviderProfile`` (``providers/base.py``:
name, base URL, env vars, request quirks) and the Omp provider wire shapes
(``packages/ai/src/providers``): each adapter builds one HTTP request from
the transcript and parses one response into the loop's assistant row. The
transport is injected, so tests run behind ``FakeTransport`` and never touch
a socket. No auth brokers, retries, streaming, or usage accounting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """A missing key, a transport failure, or an unparseable payload."""


class Transport(Protocol):
    """POST one JSON body, or GET one URL. Return the decoded JSON response."""

    def post(self, url: str, headers: dict, body: dict) -> dict: ...

    def get(self, url: str, headers: dict, params: dict) -> dict: ...


@dataclass
class Provider:
    """One adapter. Subclasses implement the wire in both directions."""

    name: str
    base_url: str
    env_vars: tuple = ()
    api_mode: str = "chat_completions"
    requires_key: bool = True

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        """Return ``(url, headers, body)`` for one turn of ``messages``."""
        raise NotImplementedError

    def parse_response(self, payload: dict) -> dict:
        """Return the loop's assistant row for one response payload."""
        raise NotImplementedError


class ProviderModel:
    """A turn-loop ``Model`` driven by one provider plus one transport.

    With a broker, the key is resolved per request URL and the agent never
    sees it: the request is built once with an empty key to learn the URL,
    the broker approves the host and resolves the key, then the request is
    rebuilt for real. Without a broker the ``api_key`` parameter rules.
    """

    def __init__(
        self,
        provider: Provider,
        model: str,
        transport: Transport,
        api_key: str = "",
        broker: Any = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.transport = transport
        self.api_key = api_key
        self.broker = broker

    def complete(self, messages: list, tools: Any = None) -> dict:
        """Build, POST, and parse one assistant message."""
        key = self.api_key
        if self.broker is not None:
            probe_url, _, _ = self.provider.build_request(
                self.model, list(messages), tools, ""
            )
            key = self.broker.key_for(self.provider, probe_url)
        if self.provider.requires_key and (not isinstance(key, str) or key == ""):
            raise ProviderError(f"{self.provider.name} needs an API key")
        url, headers, body = self.provider.build_request(
            self.model, list(messages), tools, key
        )
        try:
            payload = self.transport.post(url, headers, body)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"{self.provider.name} transport failed: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(f"{self.provider.name} returned no JSON object")
        try:
            row = self.provider.parse_response(payload)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"{self.provider.name} returned an unusable payload: {exc}"
            ) from exc
        if not isinstance(row, dict) or row.get("role") != "assistant":
            raise ProviderError(f"{self.provider.name} returned no assistant message")
        return row


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["Provider", "ProviderError", "ProviderModel", "Transport"]
