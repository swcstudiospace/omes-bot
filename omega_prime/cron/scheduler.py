"""Due-job tick. Jobs live in a JSON file.

Adapted from Hermes ``cron/scheduler_tick.py``. ``tick`` runs each job whose
``due_at`` is at or before ``now``. A one-shot job completes. An interval job
is due again at ``now + interval_seconds``.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.model import Model

HISTORY_LIMIT = 20


class JobStore:
    """One JSON file of jobs. A new store reloads what an earlier store wrote."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.jobs: list[dict] = []
        self._load()

    def schedule(
        self,
        prompt: str,
        due_at: int | float,
        *,
        interval_seconds: int | float | None = None,
    ) -> str:
        """Store one job and return its id. ``due_at`` is a unix timestamp in seconds."""
        job_id = uuid.uuid4().hex
        self.jobs.append(
            {
                "id": job_id,
                "prompt": prompt,
                "due_at": due_at,
                "interval_seconds": interval_seconds,
                "completed": False,
                "last_result": None,
                "last_ran_at": None,
                "history": [],
                "claimed_at": None,
            }
        )
        self._save()
        return job_id

    def tick(
        self,
        now: int | float,
        runner: Callable[[str], Any],
        *,
        skip_kind: str | None = None,
    ) -> list[dict]:
        """Run each due job that is not complete. Leave a later job unchanged.

        ``runner(prompt)`` is called once per due job. ``last_result`` becomes
        that value and ``last_ran_at`` becomes ``now``. An interval moves
        ``due_at`` to ``now + interval_seconds``. A one-shot job completes.
        Each execution is recorded in the job's bounded history, and a job
        already claimed or completed for ``now`` is not re-run. Jobs of
        ``skip_kind`` are left untouched (another driver owns them).
        """
        ran: list[dict] = []
        for job in self.jobs:
            if job.get("completed"):
                continue
            if skip_kind is not None and job.get("kind") == skip_kind:
                continue
            if job["due_at"] > now:
                continue
            history = job.get("history")
            if not isinstance(history, list):
                history = []
                job["history"] = history
            if job.get("claimed_at") == now:
                continue
            if any(
                isinstance(entry, dict) and entry.get("ran_at") == now
                for entry in history
            ):
                continue
            job["claimed_at"] = now
            self._save()
            job["last_result"] = runner(job["prompt"])
            job["last_ran_at"] = now
            history.append({"ran_at": now, "result": job["last_result"]})
            del history[:-HISTORY_LIMIT]
            job["claimed_at"] = None
            interval = job.get("interval_seconds")
            if interval is not None:
                job["due_at"] = now + interval
            else:
                job["completed"] = True
            ran.append(job)
        if ran:
            self._save()
        return ran

    def _load(self) -> None:
        if not self.path.exists():
            self.jobs = []
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            raise ValueError(f"job store {self.path} is not a jobs list")
        for job in jobs:
            if isinstance(job, dict):
                job.setdefault("history", [])
                job.setdefault("claimed_at", None)
        self.jobs = jobs

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"jobs": self.jobs}, ensure_ascii=False, indent=2) + "\n"
        # Write a sibling temp file and rename it over the store. `write_text`
        # truncates first, so a concurrent reader or a crash mid-write saw an
        # empty or partial file and the whole schedule was lost.
        try:
            mode: int | None = stat.S_IMODE(self.path.stat().st_mode)
        except FileNotFoundError:
            mode = None
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            if mode is not None:
                os.chmod(tmp_name, mode)
            os.replace(tmp_name, self.path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise


DESK_LEAD_KIND = "desk_lead_pass"
"""Job kind marker stored on desk lead pass jobs (Phase 64 DESK-04).

A desk pass re-runs the lead routine (:func:`run_lead_pass`) over the shared
intake store on schedule, dispatching tickets through the runtime's parent
shim. It rides the same :class:`JobStore` scheduler as everything else and
follows the v10 heartbeat precedent (61-02): jobs fire serialized — one tick
runs each due pass once, in order — and the claim is persisted to disk before
the pass starts, so no store lock is held across the model calls inside it.
"""


def schedule_desk_lead_pass(
    store: JobStore,
    *,
    due_at: int | float,
    interval_seconds: int | float,
    intake_path: str | Path | None = None,
    limit: int = 5,
    prompt: str = "run one desk lead pass",
) -> str:
    """Schedule a recurring desk lead pass and return its id.

    A pass with no interval would be a single reminder, not a desk loop, so
    like the heartbeat kind it requires a positive ``interval_seconds``.
    ``intake_path`` pins the shared ``IntakeStore`` file; ``None`` means the
    runner resolves it (state dir, then the work root). ``limit`` bounds each
    pass's ticket batch.
    """
    if isinstance(interval_seconds, bool) or interval_seconds <= 0:
        raise ValueError("a desk lead pass needs a positive interval_seconds")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    job_id = store.schedule(prompt, due_at, interval_seconds=interval_seconds)
    for job in store.jobs:
        if isinstance(job, dict) and job.get("id") == job_id:
            job["kind"] = DESK_LEAD_KIND
            job["intake_path"] = None if intake_path is None else str(intake_path)
            job["limit"] = limit
            break
    store._save()
    return job_id


def list_desk_lead_passes(store: JobStore) -> list[dict]:
    """All desk lead pass jobs, complete or not."""
    return [
        job
        for job in store.jobs
        if isinstance(job, dict) and job.get("kind") == DESK_LEAD_KIND
    ]


def desk_lead_runner(
    parent: Any = None,
    work_root: str | Path | None = None,
    *,
    bot: str = "bot-00-omega-prime",
) -> Callable[[dict], Any]:
    """Build the production runner for ``desk_lead_pass`` jobs.

    Each pass resolves the same ``IntakeStore`` the lead tools use (the
    shared state dir via :func:`desk_intake_path`) and dispatches tickets
    through the parent shim, so the routine and ``lead_intake_next`` /
    ``lead_intake_ack`` see the same records. The lead stack is imported
    inside the runner, so plain cron ticks never load it.
    """

    def runner(job: dict) -> Any:
        from omega_prime.routines.desk_lead import (
            desk_intake_path,
            make_dispatch,
            run_lead_pass,
        )
        from omega_prime.tools.lead import IntakeStore

        intake_path = job.get("intake_path") or desk_intake_path(work_root)
        intake = IntakeStore(intake_path)
        limit = job.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            limit = 5
        return run_lead_pass(
            intake, make_dispatch(parent, work_root, bot=bot), limit=limit, by=bot
        )

    return runner


def tick_desk_lead_passes(
    store: JobStore, now: int | float, lead_runner: Callable[[dict], Any]
) -> list[dict]:
    """Run each due ``desk_lead_pass`` job once, in order.

    Mirrors the v10 heartbeat tick: only desk jobs are considered, a job
    claimed or already run for ``now`` is skipped, and the claim is saved to
    disk before ``lead_runner(job)`` starts — so a concurrent tick (or
    process) sees ``claimed_at`` and nothing holds a store lock across the
    pass's model calls.
    """
    ran: list[dict] = []
    for job in store.jobs:
        if job.get("kind") != DESK_LEAD_KIND or job.get("completed"):
            continue
        if job["due_at"] > now:
            continue
        history = job.get("history")
        if not isinstance(history, list):
            history = []
            job["history"] = history
        if job.get("claimed_at") == now:
            continue
        if any(
            isinstance(entry, dict) and entry.get("ran_at") == now for entry in history
        ):
            continue
        job["claimed_at"] = now
        store._save()
        job["last_result"] = lead_runner(job)
        job["last_ran_at"] = now
        history.append({"ran_at": now, "result": job["last_result"]})
        del history[:-HISTORY_LIMIT]
        job["claimed_at"] = None
        interval = job.get("interval_seconds")
        if interval is not None:
            job["due_at"] = now + interval
        else:
            job["completed"] = True
        ran.append(job)
    if ran:
        store._save()
    return ran


def run_desk_lead_passes(
    store: JobStore,
    now: int | float,
    parent: Any = None,
    work_root: str | Path | None = None,
    *,
    bot: str = "bot-00-omega-prime",
) -> list[dict]:
    """Production entry point: tick due desk passes with real dispatch.

    ``parent`` is the runtime's in-process agent shim (``runtime.parent``)
    and ``work_root`` the runtime work root. Passes always run through a real
    dispatch closure — never ``dispatch=None``; without a parent every ticket
    comes back explicitly blocked with a failure receipt.
    """
    return tick_desk_lead_passes(
        store, now, desk_lead_runner(parent, work_root, bot=bot)
    )


def run_due_jobs(
    store: JobStore,
    now: int | float,
    model: Model,
    tools: dict[str, Any] | None,
) -> list[dict]:
    """Run each due job through a new ``Agent`` and store ``final_response``.

    ``desk_lead_pass`` jobs are skipped: they are driven by
    :func:`run_desk_lead_passes` and must never burn a model call here.
    """

    def runner(prompt: str) -> str:
        from omega_prime.agent.harness import emit
        from omega_prime.durable.journal import TurnJournal, attach_journal

        agent = Agent(model=model, tools=tools)
        try:
            journal = TurnJournal(store.path.parent / "turns.sqlite")
        except Exception as exc:
            emit(
                agent,
                "prime_degraded",
                family="durable",
                error=f"{type(exc).__name__}: {exc}",
            )
            journal = None
        attach_journal(agent, journal)
        result = run_conversation(agent, prompt)
        response = result.get("final_response") if isinstance(result, dict) else ""
        return response if isinstance(response, str) else ""

    return store.tick(now, runner, skip_kind=DESK_LEAD_KIND)


__all__ = [
    "DESK_LEAD_KIND",
    "HISTORY_LIMIT",
    "JobStore",
    "desk_lead_runner",
    "list_desk_lead_passes",
    "run_desk_lead_passes",
    "run_due_jobs",
    "schedule_desk_lead_pass",
    "tick_desk_lead_passes",
]
