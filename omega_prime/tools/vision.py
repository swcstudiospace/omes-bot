"""Image analysis through an injected transport.

Adapted from Hermes ``tools/vision_tools.py``. There is no default network client
and no image download. The transport's return value is the tool result.
"""

from __future__ import annotations

from typing import Any


def vision_analyze(
    transport: Any,
    image_url: str,
    question: str,
    region: list[Any] | None = None,
) -> Any:
    """Call ``transport.analyze(image_url, question, region=region)`` and return that payload."""
    if not isinstance(image_url, str) or not isinstance(question, str):
        return {"error": "image_url and question must be strings"}
    if transport is None:
        return {"error": "vision transport is not configured"}
    analyze = getattr(transport, "analyze", None)
    if callable(analyze):
        return analyze(image_url, question, region=region)
    if callable(transport):
        return transport(image_url, question, region=region)
    return {"error": "vision transport has no analyze"}


__all__ = ["vision_analyze"]
