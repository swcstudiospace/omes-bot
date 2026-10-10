"""Turn journal: every transcript row lands in SQLite as it is appended.

The AgentOS durable-actor shape inside one process: a crashed turn keeps
its rows with `status='open'`, and a new handle resumes from
:meth:`transcript`. The conversation loop journals at the same snapshot
points where it emits `message` events, so persisted rows match emitted
ones. Each call opens its own connection and commits.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any


class TurnJournal:
    """One SQLite file of runs plus their ordered rows."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs "
                "(run_id TEXT PRIMARY KEY, status TEXT, final_response TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS rows "
                "(run_id TEXT, seq INTEGER, row TEXT, PRIMARY KEY (run_id, seq))"
            )
            connection.commit()
        finally:
            connection.close()

    def begin_run(self, run_id: str) -> None:
        """Open a run. An existing run keeps its rows and status."""
        connection = self._connect()
        try:
            connection.execute(
                "INSERT OR IGNORE INTO runs (run_id, status, final_response)"
                " VALUES (?, 'open', '')",
                (run_id,),
            )
            connection.commit()
        finally:
            connection.close()

    def append(self, run_id: str, row: dict) -> None:
        """Store one row as the next seq. Unknown runs open first."""
        self.begin_run(run_id)
        connection = self._connect()
        try:
            found = connection.execute(
                "SELECT COALESCE(MAX(seq), -1) FROM rows WHERE run_id = ?", (run_id,)
            ).fetchone()
            seq = int(found[0]) + 1
            connection.execute(
                "INSERT INTO rows (run_id, seq, row) VALUES (?, ?, ?)",
                (run_id, seq, json.dumps(row, ensure_ascii=False, default=str)),
            )
            connection.commit()
        finally:
            connection.close()

    def finish_run(self, run_id: str, status: str, final_response: str = "") -> None:
        """Close a run with its exit status and final response."""
        self.begin_run(run_id)
        connection = self._connect()
        try:
            connection.execute(
                "UPDATE runs SET status = ?, final_response = ? WHERE run_id = ?",
                (str(status), str(final_response), run_id),
            )
            connection.commit()
        finally:
            connection.close()

    def transcript(self, run_id: str) -> list[dict[str, Any]]:
        """Rows in seq order. Unknown runs yield ``[]``."""
        connection = self._connect()
        try:
            found = connection.execute(
                "SELECT row FROM rows WHERE run_id = ? ORDER BY seq ASC", (run_id,)
            ).fetchall()
        finally:
            connection.close()
        return [json.loads(row[0]) for row in found]

    def open_runs(self) -> list[str]:
        """Run ids still `open`, in first-row order."""
        connection = self._connect()
        try:
            found = connection.execute(
                "SELECT r.run_id FROM runs r WHERE r.status = 'open'"
                " ORDER BY (SELECT COALESCE(MIN(seq), -1) FROM rows"
                " WHERE rows.run_id = r.run_id) ASC, r.run_id ASC"
            ).fetchall()
        finally:
            connection.close()
        return [row[0] for row in found]

    def status(self) -> dict[str, Any]:
        """Cheap counts: open runs, row count, and the last run id."""
        connection = self._connect()
        try:
            runs = connection.execute(
                "SELECT run_id, status FROM runs ORDER BY run_id"
            ).fetchall()
            found = connection.execute("SELECT COUNT(*) FROM rows").fetchone()
        finally:
            connection.close()
        count = int(found[0]) if found is not None else 0
        return {
            "present": True,
            "runs": len(runs),
            "open_runs": sum(1 for row in runs if row[1] == "open"),
            "entry_count": count,
            "last_run_id": runs[-1][0] if runs else None,
        }

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))


class GuardedJournal:
    """A journal whose failures are reported and then ignored.

    The turn continues. ``sink`` receives ``type``, ``family``, and
    ``error`` keyword arguments; a sink that itself raises is ignored.
    """

    def __init__(self, inner: TurnJournal, sink: Any = None) -> None:
        self._inner = inner
        self.path = inner.path
        self._sink = sink

    def begin_run(self, run_id: str) -> None:
        self._call("begin_run", run_id)

    def append(self, run_id: str, row: dict) -> None:
        self._call("append", run_id, row)

    def finish_run(self, run_id: str, status: str, final_response: str = "") -> None:
        self._call("finish_run", run_id, status, final_response)

    def transcript(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._call("transcript", run_id)
        return rows if isinstance(rows, list) else []

    def open_runs(self) -> list[str]:
        runs = self._call("open_runs")
        return runs if isinstance(runs, list) else []

    def status(self) -> dict[str, Any]:
        found = self._call("status")
        return found if isinstance(found, dict) else {"present": False}

    def _call(self, method: str, *args: Any) -> Any:
        try:
            return getattr(self._inner, method)(*args)
        except Exception as exc:
            sink = self._sink
            if sink is not None:
                with contextlib.suppress(Exception):
                    sink(
                        type="prime_degraded",
                        family="durable",
                        error=f"{type(exc).__name__}: {exc}",
                    )
            return None


def attach_journal(agent: Any, journal: TurnJournal | None) -> None:
    """Point ``agent.journal`` at a guarded copy of ``journal``.

    Failures emit ``prime_degraded`` on ``agent`` and the turn continues.
    """
    if journal is None:
        return
    from omega_prime.agent.harness import emit

    def sink(**fields: Any) -> None:
        event_type = fields.pop("type", "prime_degraded")
        if not isinstance(event_type, str):
            event_type = "prime_degraded"
        emit(agent, event_type, **fields)

    agent.journal = GuardedJournal(journal, sink)


__all__ = ["GuardedJournal", "TurnJournal", "attach_journal"]
