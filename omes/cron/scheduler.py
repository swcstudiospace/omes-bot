"""Due-job tick. Jobs live in a JSON file.

Adapted from Hermes ``cron/scheduler_tick.py``. ``tick`` runs each job whose
``due_at`` is at or before ``now``. A one-shot job completes. An interval job
is due again at ``now + interval_seconds``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.model import Model


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
            }
        )
        self._save()
        return job_id

    def tick(self, now: int | float, runner: Callable[[str], str]) -> list[dict]:
        """Run each due job that is not complete. Leave a later job unchanged.

        ``runner(prompt)`` is called once per due job. ``last_result`` becomes
        that string and ``last_ran_at`` becomes ``now``. An interval moves
        ``due_at`` to ``now + interval_seconds``. A one-shot job completes.
        """
        ran: list[dict] = []
        for job in self.jobs:
            if job.get("completed"):
                continue
            if job["due_at"] > now:
                continue
            job["last_result"] = runner(job["prompt"])
            job["last_ran_at"] = now
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
        self.jobs = jobs

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"jobs": self.jobs}, ensure_ascii=False, indent=2) + "\n"
        self.path.write_text(text, encoding="utf-8")


def run_due_jobs(
    store: JobStore,
    now: int | float,
    model: Model,
    tools: dict[str, Any] | None,
) -> list[dict]:
    """Run each due job through a new ``Agent`` and store ``final_response``."""

    def runner(prompt: str) -> str:
        agent = Agent(model=model, tools=tools)
        result = run_conversation(agent, prompt)
        response = result.get("final_response") if isinstance(result, dict) else ""
        return response if isinstance(response, str) else ""

    return store.tick(now, runner)


__all__ = ["JobStore", "run_due_jobs"]
