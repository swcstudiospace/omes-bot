"""Tool registry.

Adapted from Hermes ``tools/registry.py``. A tool is a name, a description, a JSON
schema for its parameters, and a handler. ``dispatch`` always returns a JSON string.
An unknown name becomes a JSON error and does not raise. Handlers return
JSON-serializable objects; this module encodes them.
"""

from __future__ import annotations

import copy
import inspect
import json
from collections.abc import Callable
from typing import Any


class ToolRegistry:
    """In-process tool map. ``dispatch`` calls the handler and encodes its result."""

    def __init__(self) -> None:
        self._tools: dict[str, _Tool] = {}
        self._order: list[str] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Any],
    ) -> None:
        """Store ``handler`` under ``name``. Registering the same name replaces it."""
        if not isinstance(name, str) or not name:
            raise ValueError("tool name must be a non-empty string")
        if not isinstance(description, str):
            raise ValueError("description must be a string")
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be a JSON schema object")
        if not callable(handler):
            raise ValueError("handler must be callable")
        self._tools[name] = _Tool(name, description, copy.deepcopy(parameters), handler)
        if name not in self._order:
            self._order.append(name)

    def schemas(self) -> list[dict]:
        """OpenAI-style function schemas, in registration order."""
        return [_schema(self._tools[name]) for name in self._order if name in self._tools]

    def dispatch(self, name: str, arguments: Any = None) -> str:
        """Run ``name`` and return a JSON string. Unknown names do not raise."""
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            label = name if isinstance(name, str) else type(name).__name__
            return _dump({"error": f"Unknown tool: {label}"})
        try:
            payload = _call(tool.handler, _arguments(arguments))
        except Exception as exc:
            return _dump({"error": f"{type(exc).__name__}: {exc}"})
        try:
            return _dump(payload)
        except (TypeError, ValueError):
            return _dump({"error": "tool result is not JSON-serializable"})


class _Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler


def _schema(tool: _Tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": copy.deepcopy(tool.parameters),
        },
    }


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _arguments(arguments: Any) -> dict:
    if arguments is None:
        return {}
    if isinstance(arguments, str):
        parsed = json.loads(arguments)
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be a JSON object")
        return parsed
    if isinstance(arguments, dict):
        return arguments
    raise ValueError("arguments must be an object")


def _call(handler: Callable[..., Any], arguments: dict) -> Any:
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return handler(**arguments)
    parameters = signature.parameters
    if any(item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters.values()):
        return handler(**arguments)
    accepted = {
        name
        for name, item in parameters.items()
        if item.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    missing = [
        name
        for name, item in parameters.items()
        if name in accepted and item.default is inspect.Parameter.empty and name not in arguments
    ]
    if missing:
        raise TypeError("missing required arguments: " + ", ".join(missing))
    extra = [name for name in arguments if name not in accepted]
    if extra:
        raise TypeError("unexpected arguments: " + ", ".join(extra))
    return handler(**{name: arguments[name] for name in accepted if name in arguments})


__all__ = ["ToolRegistry"]
