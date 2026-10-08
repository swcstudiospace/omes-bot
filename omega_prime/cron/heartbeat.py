# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Session heartbeat — a cron job kind that re-enters a named session.

Behavior port of Prime Agent's heartbeat (``rlm-heartbeat`` skill +
``pa-core/src/cron/``) @ ``967eb13f`` (MIT, PrimeIntellect). A heartbeat is a
recurring job whose prompt re-enters a named session on schedule, riding the
existing :class:`JobStore` scheduler (LOOP-02). Jobs fire serialized (the v4
rule): one tick runs each due heartbeat once, in order.

The heartbeat prompt carries the target session name so the runner re-enters
that session rather than starting a fresh conversation.
"""

from __future__ import annotations

from typing import Any

from omega_prime.cron.scheduler import JobStore

#: Job kind marker stored on heartbeat jobs.
HEARTBEAT_KIND = "session_heartbeat"


def schedule_heartbeat(
    store: JobStore,
    session: str,
    prompt: str,
    *,
    interval_seconds: int | float,
    due_at: int | float,
) -> str:
    """Schedule a recurring heartbeat that re-enters ``session`` with ``prompt``.

    Heartbeats are interval jobs (a heartbeat with no interval is a single
    reminder, not a heartbeat). Returns the job id.
    """
    if not isinstance(session, str) or not session.strip():
        raise ValueError("session must be a non-empty string")
    if isinstance(interval_seconds, bool) or interval_seconds <= 0:
        raise ValueError("a heartbeat needs a positive interval_seconds")
    job_id = store.schedule(prompt, due_at, interval_seconds=interval_seconds)
    for job in store.jobs:
        if job["id"] == job_id:
            job["kind"] = HEARTBEAT_KIND
            job["session"] = session
            break
    store._save()
    return job_id


def list_heartbeats(store: JobStore) -> list[dict]:
    """All heartbeat jobs, complete or not."""
    return [job for job in store.jobs if job.get("kind") == HEARTBEAT_KIND]


def clear_heartbeat(store: JobStore, job_id: str) -> dict:
    """Remove one heartbeat by id. Unknown id is a structured result."""
    for index, job in enumerate(store.jobs):
        if job["id"] == job_id and job.get("kind") == HEARTBEAT_KIND:
            store.jobs.pop(index)
            store._save()
            return {"cleared": job_id}
    return {"error": f"no heartbeat job: {job_id!r}"}


def heartbeat_runner(session_runner: Any) -> Any:
    """Build a ``runner(prompt)`` that re-enters the job's named session.

    ``session_runner(session, prompt)`` runs one turn in the named session
    and returns its final response. The JobStore tick passes only the prompt,
    so the session is bound through the job dict at tick time by
    :func:`tick_heartbeats`.
    """

    def runner(session: str, prompt: str) -> Any:
        return session_runner(session, prompt)

    return runner


def tick_heartbeats(
    store: JobStore, now: int | float, session_runner: Any
) -> list[dict]:
    """Run each due heartbeat, re-entering its named session.

    Like :meth:`JobStore.tick` but the runner receives the job's ``session``
    so the turn re-enters the named session. Only heartbeat jobs are considered.
    """
    ran: list[dict] = []
    for job in store.jobs:
        if job.get("kind") != HEARTBEAT_KIND or job.get("completed"):
            continue
        if job["due_at"] > now:
            continue
        history = job.setdefault("history", [])
        if job.get("claimed_at") == now:
            continue
        if any(isinstance(e, dict) and e.get("ran_at") == now for e in history):
            continue
        job["claimed_at"] = now
        store._save()
        job["last_result"] = session_runner(job.get("session", ""), job["prompt"])
        job["last_ran_at"] = now
        history.append({"ran_at": now, "result": job["last_result"]})
        del history[:-20]
        job["claimed_at"] = None
        job["due_at"] = now + job["interval_seconds"]
        ran.append(job)
    if ran:
        store._save()
    return ran


__all__ = [
    "HEARTBEAT_KIND",
    "clear_heartbeat",
    "heartbeat_runner",
    "list_heartbeats",
    "schedule_heartbeat",
    "tick_heartbeats",
]
