"""In-memory task list.

Adapted from Hermes ``tools/todo_tool.py``. ``todo_write`` replaces the whole list.
It does not merge by id. ``todo_read`` returns that list.
"""

from __future__ import annotations

import copy
from typing import Any


class TodoStore:
    """One task list. Callers receive copies, so a later edit cannot alias the store."""

    def __init__(self) -> None:
        self._items: list[Any] = []

    def replace(self, todos: list[Any]) -> None:
        self._items = copy.deepcopy(todos)

    def read(self) -> list[Any]:
        return copy.deepcopy(self._items)


def todo_write(store: TodoStore, todos: list[Any]) -> dict[str, Any]:
    """Replace ``store`` with a copy of ``todos`` and return the stored list."""
    if not isinstance(todos, list):
        return {"error": "todos must be a list"}
    store.replace(todos)
    return {"todos": store.read()}


def todo_read(store: TodoStore) -> dict[str, Any]:
    """Return a copy of the list last stored by ``todo_write``."""
    return {"todos": store.read()}


__all__ = ["TodoStore", "todo_read", "todo_write"]
