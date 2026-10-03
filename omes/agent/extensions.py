"""Extension hooks that run around the model call.

Ports the ``packages/coding-agent/src/extensibility/hooks`` runner shape for
one event: ``before_model`` hooks run in registration order, may mutate the
outgoing messages in place, and the first ``{"stop": True, ...}`` verdict
wins — later hooks do not run. No plugin loader ships here; hosts register
plain callables.
"""

from __future__ import annotations

from typing import Any


class ExtensionHooks:
    """Named hook lists. Only ``before_model`` exists today."""

    def __init__(self) -> None:
        self.before_model: list[Any] = []

    def register_before_model(self, fn: Any) -> None:
        """Append a ``fn(messages, tools)`` hook."""
        if not callable(fn):
            raise TypeError("hook must be callable")
        self.before_model.append(fn)

    def run_before_model(self, messages: list, tools: Any) -> dict | None:
        """Run each hook. The first stop verdict wins; else None."""
        for hook in self.before_model:
            verdict = hook(messages, tools)
            if isinstance(verdict, dict) and verdict.get("stop"):
                return verdict
        return None


__all__ = ["ExtensionHooks"]
