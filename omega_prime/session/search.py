"""Store messages in SQLite and find them by a literal substring.

An empty query is an error and returns no rows. A new ``SessionStore`` on the
same file sees a message the previous store appended.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SessionStore:
    """One SQLite file. Each call opens its own connection and commits."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def append(self, session_id: str, role: str, content: str) -> None:
        """Store one message."""
        connection = self._connect()
        try:
            connection.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            connection.commit()
        finally:
            connection.close()

    def matching(self, query: str) -> list[dict[str, Any]]:
        """Rows whose content contains ``query`` as a literal substring, in insert order."""
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT id, session_id, role, content FROM messages ORDER BY id ASC"
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
            if isinstance(row["content"], str) and query in row["content"]
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


def session_search(query: str, *, store: SessionStore) -> str:
    """JSON ``messages`` for a literal substring. An empty query is an error and has no rows."""
    if not isinstance(query, str) or query == "":
        return json.dumps(
            {"success": False, "error": "query must be a non-empty string."},
            ensure_ascii=False,
        )
    return json.dumps(
        {"success": True, "messages": store.matching(query)}, ensure_ascii=False
    )


__all__ = ["SessionStore", "session_search"]
