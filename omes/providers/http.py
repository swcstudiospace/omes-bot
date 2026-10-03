"""Real HTTP transport for providers: stdlib only, retries, host allowlist.

`HttpTransport` implements the `Transport.post` seam over `http.client`:
JSON request bodies, JSON responses, per-call timeouts, and retries on
connection failures, timeouts, and HTTP 5xx. With a seat policy attached,
hosts outside the allowlist are refused before any socket exists.

The `connect` factory (default: stdlib HTTP/HTTPS connections) exists so
tests can run the same request/response framing over a socketpair to a
scripted peer that speaks real HTTP bytes.
"""

from __future__ import annotations

import http.client
import json
import socket
import time
from typing import Any, Callable
from urllib.parse import urlsplit

from omes.providers.base import ProviderError


class HttpTransport:
    """POST JSON over HTTP. `max_retries` counts retries after the first try."""

    def __init__(
        self,
        policy: Any = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        backoff: float = 0.1,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive number of seconds")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self._policy = policy
        self._timeout = float(timeout)
        self._max_retries = max_retries
        self._backoff = backoff
        self._connect = connect or _stdlib_connect

    def post(self, url: str, headers: dict, body: dict) -> dict:
        """POST one JSON body. Return the decoded JSON response."""
        host, port, path, use_tls = _split(url)
        if host is None:
            raise ProviderError(f"cannot parse request host from {url!r}")
        if self._policy is not None and not self._policy.allows_host(host):
            raise ProviderError(f"network blocked to host {host}")
        payload = json.dumps(body).encode("utf-8")
        merged = {"Content-Type": "application/json", "Content-Length": str(len(payload))}
        merged.update(headers or {})
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._once(host, port, path, use_tls, merged, payload, url)
            except _Retryable as exc:
                last = exc
                if attempt < self._max_retries and self._backoff > 0:
                    time.sleep(self._backoff * (attempt + 1))
            except ProviderError:
                raise
        assert last is not None
        raise ProviderError(f"request to {host} failed after retries: {last}") from last

    def _once(
        self,
        host: str,
        port: int,
        path: str,
        use_tls: bool,
        headers: dict,
        payload: bytes,
        url: str,
    ) -> dict:
        try:
            connection = self._connect(host, port, self._timeout, use_tls)
        except OSError as exc:
            raise _Retryable(str(exc) or type(exc).__name__) from exc
        try:
            try:
                connection.request("POST", path, body=payload, headers=headers)
                response = connection.getresponse()
                status = response.status
                raw = response.read()
            except (http.client.HTTPException, TimeoutError, socket.timeout, OSError) as exc:
                raise _Retryable(str(exc) or type(exc).__name__) from exc
        finally:
            try:
                connection.close()
            except OSError:
                pass
        if 500 <= status <= 599:
            raise _Retryable(f"HTTP {status}")
        if 400 <= status <= 499:
            raise ProviderError(f"HTTP {status} from {url}")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"response is not JSON: {exc}") from exc
        if not isinstance(decoded, dict):
            raise ProviderError("response is not a JSON object")
        return decoded


class _Retryable(Exception):
    """A failure worth one more attempt."""


def _stdlib_connect(
    host: str, port: int, timeout: float, use_tls: bool
) -> http.client.HTTPConnection:
    """Open a real stdlib connection."""
    if use_tls:
        return http.client.HTTPSConnection(host, port, timeout=timeout)
    return http.client.HTTPConnection(host, port, timeout=timeout)


def _split(url: str) -> tuple[str | None, int, str, bool]:
    if not isinstance(url, str) or url == "":
        return None, 0, "/", False
    try:
        parts = urlsplit(url)
    except ValueError:
        return None, 0, "/", False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None, 0, "/", False
    host = parts.hostname.lower()
    use_tls = parts.scheme == "https"
    port = parts.port or (443 if use_tls else 80)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return host, port, path, use_tls


__all__ = ["HttpTransport"]
