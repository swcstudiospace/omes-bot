"""Model call surface for the turn loop.

``ScriptedModel`` replays assistant messages and records what it was shown.
No network and no provider SDK.
"""

from __future__ import annotations

from typing import Any, Protocol


class Model(Protocol):
    def complete(self, messages: list, tools: Any = None) -> dict:
        """Return one assistant message for this iteration."""


class ScriptedModel:
    """Return scripted assistant messages in order and record each request.

    ``seen`` holds a shallow copy of the message list taken at the call, so a
    later append does not change what this call observed. Content strings are
    the same objects the loop passed in.
    """

    def __init__(self, script: list[dict]):
        self._script = [dict(message) for message in script]
        self.seen: list[list] = []
        self.tools_seen: list[Any] = []
        self.call_count = 0

    @property
    def remaining(self) -> int:
        return len(self._script)

    def complete(self, messages: list, tools: Any = None) -> dict:
        self.call_count += 1
        snapshot: list = []
        for message in messages:
            snapshot.append(dict(message) if isinstance(message, dict) else message)
        self.seen.append(snapshot)
        self.tools_seen.append(tools)
        if self._script:
            return self._script.pop(0)
        return {"role": "assistant", "content": ""}


__all__ = ["Model", "ScriptedModel"]
