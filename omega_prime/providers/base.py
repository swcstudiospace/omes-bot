"""Provider contract feeding real models into the turn loop.

Ports the declarative Hermes ``ProviderProfile`` (``providers/base.py``:
name, base URL, env vars, request quirks) and the Omp provider wire shapes
(``packages/ai/src/providers``): each adapter builds one HTTP request from
the transcript and parses one response into the loop's assistant row. The
transport is injected, so tests run behind ``FakeTransport`` and never touch
a socket. Retries live in the transport; usage is recorded per call. No
streaming yet.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """A missing key, a transport failure, or an unparseable payload."""


class Transport(Protocol):
    """POST one JSON body, GET one URL, or stream response lines."""

    def post(self, url: str, headers: dict, body: dict) -> dict: ...

    def get(self, url: str, headers: dict, params: dict) -> dict: ...

    def stream(self, url: str, headers: dict, body: dict) -> Iterator[str]: ...


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

    def parse_usage(self, payload: dict) -> dict[str, int] | None:
        """Normalized usage from one response payload. None when absent."""
        raise NotImplementedError

    def stream_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        """Streaming variant of ``build_request``. Adds ``stream: true``."""
        url, headers, body = self.build_request(model, messages, tools, api_key)
        return url, headers, {**body, "stream": True}

    def parse_stream(self, lines: Any) -> tuple[dict[str, Any], dict[str, int] | None]:
        """Accumulate streamed lines into ``(assistant row, usage?)``."""
        raise NotImplementedError

    def fallback_request(
        self,
        model: str,
        messages: list,
        tools: Any,
        api_key: str,
        error: ProviderError,
    ) -> tuple[str, dict, dict] | None:
        """Alternate request after ``error``. None surfaces the error."""
        return None

    def _sse_data(self, lines: Any) -> Iterator[dict[str, Any]]:
        """Decoded JSON bodies from SSE ``data:`` lines. Skips junk."""
        if lines is None:
            return
        for line in lines:
            if not isinstance(line, str):
                continue
            text = line.strip()
            if not text.startswith("data:"):
                continue
            data = text[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                decoded = json.loads(data)
            except ValueError:
                continue
            if isinstance(decoded, dict):
                yield decoded

    def _usage_from(
        self,
        payload: dict,
        section: str | None,
        pairs: tuple[tuple[str, str], ...],
    ) -> dict[str, int] | None:
        """Pick normalized int counters from a payload section."""
        node = payload if section is None else payload.get(section)
        if not isinstance(node, dict):
            return None
        found: dict[str, int] = {}
        for wire, normalized in pairs:
            value = node.get(wire)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                found[normalized] = value
        return found or None


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
        stream: bool = False,
    ) -> None:
        self.provider = provider
        self.model = model
        self.transport = transport
        self.api_key = api_key
        self.broker = broker
        self.stream = stream
        self.last_usage: dict[str, int] | None = None
        self.last_fallback = False

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
        self.last_fallback = False
        if self.stream:
            return self._complete_stream(messages, tools, key)
        url, headers, body = self.provider.build_request(
            self.model, list(messages), tools, key
        )
        payload = self._post_with_fallback(url, headers, body, messages, tools, key)
        return self._parse(payload)

    def _post_with_fallback(
        self,
        url: str,
        headers: dict,
        body: dict,
        messages: list,
        tools: Any,
        key: str,
    ) -> dict:
        """POST once, or twice when the provider offers a fallback request."""
        try:
            return self._post(url, headers, body)
        except ProviderError as exc:
            alt = self.provider.fallback_request(
                self.model, list(messages), tools, key, exc
            )
            if alt is None:
                raise
            self.last_fallback = True
            alt_url, alt_headers, alt_body = alt
            return self._post(alt_url, alt_headers, alt_body)

    def _post(self, url: str, headers: dict, body: dict) -> dict:
        """POST one request. Return the JSON object payload."""
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
        return payload

    def _parse(self, payload: dict) -> dict:
        """Parse and record usage for one assistant message."""
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
        self.last_usage = self.provider.parse_usage(payload)
        return row

    def _complete_stream(self, messages: list, tools: Any, key: str) -> dict:
        """Accumulate one assistant message from streamed lines."""
        streamer = getattr(self.transport, "stream", None)
        if streamer is None:
            raise ProviderError(f"{self.provider.name} transport does not stream")
        url, headers, body = self.provider.stream_request(
            self.model, list(messages), tools, key
        )
        try:
            row, usage = self.provider.parse_stream(streamer(url, headers, body))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"{self.provider.name} stream failed: {exc}") from exc
        if not isinstance(row, dict) or row.get("role") != "assistant":
            raise ProviderError(f"{self.provider.name} returned no assistant message")
        self.last_usage = usage
        return row


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["Provider", "ProviderError", "ProviderModel", "Transport"]
