# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""The job store replaces its file atomically.

`JobStore._save` used to truncate and rewrite `jobs.json` in place, so a reader
racing a save (or a crash mid-write) saw an empty file. That made
`test_apscheduler_backend` fail intermittently in CI and put the whole schedule
at risk of corruption.
"""

from __future__ import annotations

import json
import os
import stat
import threading
from pathlib import Path

import pytest

from omega_prime.cron.scheduler import JobStore


def test_save_leaves_only_the_store_file(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.json")
    store.schedule("hello", 1)
    store.schedule("again", 2)
    assert [p.name for p in tmp_path.iterdir()] == ["jobs.json"]
    persisted = json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8"))
    assert [job["prompt"] for job in persisted["jobs"]] == ["hello", "again"]


def test_a_reader_never_sees_a_partial_store(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    store = JobStore(path)
    store.schedule("seed", 0)
    stop = threading.Event()
    errors: list[Exception] = []

    def reader() -> None:
        while not stop.is_set():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # truncated file or a missing store
                errors.append(exc)

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        for i in range(300):
            store.schedule(f"job-{i}", i)
    finally:
        stop.set()
        thread.join()
    assert errors == []


def test_a_failed_replace_keeps_the_previous_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "jobs.json"
    store = JobStore(path)
    store.schedule("keep", 1)
    before = path.read_text(encoding="utf-8")

    def boom(src: str, dst: str) -> None:
        del src, dst
        raise OSError("disk went away")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="disk went away"):
        store.schedule("lost", 2)
    monkeypatch.undo()
    assert path.read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == ["jobs.json"]


def test_an_existing_store_keeps_its_file_mode(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    store = JobStore(path)
    store.schedule("first", 1)
    os.chmod(path, 0o640)
    store.schedule("second", 2)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
