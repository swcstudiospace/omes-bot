"""Phase 24: JobStore jobs firing through a real APScheduler."""

from __future__ import annotations

import json
import time
from pathlib import Path

from omega_prime.cron.apscheduler_backend import SchedulerService
from omega_prime.cron.scheduler import JobStore


def _wait_until(predicate, *, deadline=10.0):
    start = time.monotonic()
    while time.monotonic() - start < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _store_for(path: Path) -> JobStore:
    return JobStore(path / "jobs.json")


def _recorder(seen: list[str], reply: str):
    def _run(prompt: str) -> str:
        seen.append(prompt)
        return reply

    return _run


def test_one_shot_fires_once_and_persists(tmp_path: Path):
    store = _store_for(tmp_path)
    seen: list[str] = []
    job_id = store.schedule("hello", time.time() + 0.2)
    service = SchedulerService(store, _recorder(seen, "done"))
    try:
        assert service.start() == []
        assert _wait_until(lambda: seen == ["hello"])
        job = next(entry for entry in store.jobs if entry["id"] == job_id)
        # The runner is called before the tick marks the job complete and saves
        # it, so wait for those postconditions rather than for the call itself.
        assert _wait_until(lambda: job["completed"] is True)
        assert job["last_result"] == "done"
        assert len(job["history"]) == 1
        jobs_file = tmp_path / "jobs.json"

        def persisted_result() -> object:
            # The store replaces the file atomically: every read parses.
            return json.loads(jobs_file.read_text(encoding="utf-8"))["jobs"][0][
                "last_result"
            ]

        assert _wait_until(lambda: persisted_result() == "done")
    finally:
        service.stop()


def test_interval_job_fires_repeatedly(tmp_path: Path):
    store = _store_for(tmp_path)
    seen: list[str] = []
    first_due = time.time() + 0.2
    store.schedule("beat", first_due, interval_seconds=0.2)
    service = SchedulerService(store, _recorder(seen, "beat-done"))
    try:
        service.start()
        job = store.jobs[0]
        # History is appended after the runner returns, so wait for it too.
        assert _wait_until(lambda: len(seen) >= 2 and len(job["history"]) >= 2)
        assert job["completed"] is False
        assert job["due_at"] > first_due
    finally:
        service.stop()


def test_shared_due_date_runs_each_job_once(tmp_path: Path):
    store = _store_for(tmp_path)
    seen: list[str] = []
    due = time.time() + 0.2
    store.schedule("one", due)
    store.schedule("two", due)
    service = SchedulerService(store, _recorder(seen, "ok"))
    try:
        service.start()
        assert _wait_until(lambda: sorted(seen) == ["one", "two"])
        time.sleep(0.3)
        assert sorted(seen) == ["one", "two"]
        assert all(entry["completed"] for entry in store.jobs)
    finally:
        service.stop()


def test_restart_resumes_without_duplicates(tmp_path: Path):
    store = _store_for(tmp_path)
    seen: list[str] = []
    store.schedule("beat", time.time() + 0.2, interval_seconds=0.3)
    first = SchedulerService(store, _recorder(seen, "ok"))
    try:
        first.start()
        assert _wait_until(lambda: len(seen) >= 1)
    finally:
        first.stop()
    reopened = JobStore(tmp_path / "jobs.json")
    assert len(reopened.jobs[0]["history"]) >= 1
    second = SchedulerService(reopened, _recorder(seen, "ok"))
    try:
        second.start()
        count_at_restart = len(seen)
        assert _wait_until(lambda: len(seen) > count_at_restart)
        assert len(reopened.jobs[0]["history"]) == len(seen)
    finally:
        second.stop()


def test_overdue_jobs_run_on_start(tmp_path: Path):
    store = _store_for(tmp_path)
    store.schedule("late", time.time() - 5)
    service = SchedulerService(store, lambda prompt: "late-done")
    try:
        ran = service.start()
        assert [entry["prompt"] for entry in ran] == ["late"]
        assert store.jobs[0]["completed"] is True
        assert service.job_ids == []
    finally:
        service.stop()


def test_double_start_registers_once_and_stop_is_safe(tmp_path: Path):
    store = _store_for(tmp_path)
    store.schedule("hello", time.time() + 30)
    service = SchedulerService(store, lambda prompt: "ok")
    try:
        service.stop()
        service.start()
        service.start()
        assert service.job_ids == [store.jobs[0]["id"]]
    finally:
        service.stop()
