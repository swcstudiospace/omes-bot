"""Web search and extract through an injected transport.

Adapted from Hermes ``tools/web_tools.py``. There is no default network client.
A missing transport is an error. The transport's return value is the tool result.
"""

from __future__ import annotations

from typing import Any


def web_search(transport: Any, query: str, limit: int = 5) -> Any:
    """Call ``transport.search(query, limit=limit)`` and return that payload."""
    if not isinstance(query, str):
        return {"error": "query must be a string"}
    return _call(transport, "search", query, limit=limit)


def web_extract(transport: Any, urls: list[Any]) -> Any:
    """Call ``transport.extract(urls)`` and return that payload."""
    if not isinstance(urls, list):
        return {"error": "urls must be a list"}
    return _call(transport, "extract", urls)


def _call(transport: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if transport is None:
        return {"error": "web transport is not configured"}
    fn = getattr(transport, method, None)
    if callable(fn):
        return fn(*args, **kwargs)
    if callable(transport):
        return transport(method, *args, **kwargs)
    return {"error": f"web transport has no {method}"}


__all__ = ["web_extract", "web_search"]
