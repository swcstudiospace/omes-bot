# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for snapshot restore (rollback)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
import time
from pathlib import Path

import pytest

from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.rollback import RollbackError, rollback
from omega_prime.grokbot.upgrade import (
    SnapshotCorruptError,
    SnapshotMissingError,
    snapshot,
    verify_snapshot,
)


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _seed_state(root: Path) -> list[Path]:
    return [
        _write(root / "state.json", b'{"v": 1}'),
        _write(root / "token-store.json", b'{"version": 1, "tokens": []}'),
        _write(root / "manifest.json", b'{"name": "omega-prime"}'),
    ]


def _read_table(snap: Path, name: str) -> dict[str, str]:
    raw: object = json.loads((snap / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return dict(raw)


def _mutate(paths: list[Path]) -> None:
    for path in paths:
        path.write_bytes(path.read_bytes() + b"\ncorrupted")


def test_rollback_round_trip_digest_match(tmp_path: Path) -> None:
    src = tmp_path / "live"
    sources = _seed_state(src)
    original = {p: p.read_bytes() for p in sources}
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)

    result = rollback(snap, sources)

    assert result["restored"] == [str(p) for p in sources]
    assert result["dry_run"] is False
    digests = _read_table(snap, "digests.json")
    origins = _read_table(snap, "sources.json")
    for rel, dest in origins.items():
        assert Path(dest).read_bytes() == original[Path(dest)]
        assert hashlib.sha256(Path(dest).read_bytes()).hexdigest() == digests[rel]


def test_rollback_dry_run_writes_nothing(tmp_path: Path) -> None:
    src = tmp_path / "live"
    sources = _seed_state(src)
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)
    before = {p: p.read_bytes() for p in sources}
    before_snapshots = sorted(p.name for p in (tmp_path / "snapshots").iterdir())

    result = rollback(snap, sources, dry_run=True)

    assert result["restored"] == [str(p) for p in sources]
    assert result["dry_run"] is True
    assert result["pre_rollback_snapshot"] is None
    for path in sources:
        assert path.read_bytes() == before[path]
    assert sorted(p.name for p in (tmp_path / "snapshots").iterdir()) == (
        before_snapshots
    )


def test_rollback_missing_snapshot_raises(tmp_path: Path) -> None:
    target = _write(tmp_path / "live" / "state.json", b'{"v": 1}')
    with pytest.raises(SnapshotMissingError, match="no-snapshot"):
        rollback(tmp_path / "no-snapshot", [target])

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SnapshotMissingError, match=r"digests\.json"):
        rollback(empty, [target])


def test_rollback_pre_snapshot_created(tmp_path: Path) -> None:
    src = tmp_path / "live"
    sources = _seed_state(src)
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)
    mutated = {p: p.read_bytes() for p in sources}

    result = rollback(snap, sources)

    pre = Path(str(result["pre_rollback_snapshot"]))
    assert pre == tmp_path / "snapshots" / "pre-rollback"
    assert verify_snapshot(pre) == []
    pre_origins = _read_table(pre, "sources.json")
    for rel, dest in pre_origins.items():
        assert (pre / rel).read_bytes() == mutated[Path(dest)]


def test_rollback_replaces_corrupt_live_file(tmp_path: Path) -> None:
    src = tmp_path / "live"
    sources = _seed_state(src)
    victim = sources[0]
    expected = victim.read_bytes()
    snap = snapshot(sources, tmp_path / "snapshots")
    victim.write_bytes(b"\x00\xff not-json \xfe garbage")

    rollback(snap, [victim])

    assert victim.read_bytes() == expected
    digests = _read_table(snap, "digests.json")
    origins = _read_table(snap, "sources.json")
    rel = next(rel for rel, dest in origins.items() if Path(dest) == victim)
    assert hashlib.sha256(victim.read_bytes()).hexdigest() == digests[rel]


def test_rollback_unknown_target_raises(tmp_path: Path) -> None:
    sources = _seed_state(tmp_path / "live")
    snap = snapshot(sources, tmp_path / "snapshots")
    with pytest.raises(RollbackError, match="no entry in snapshot"):
        rollback(snap, [tmp_path / "live" / "never-snapshotted.json"])


def test_rollback_appends_audit_record(tmp_path: Path) -> None:
    src = tmp_path / "live"
    sources = _seed_state(src)
    audit_log = src / "audit.jsonl"
    tracer = GrokBotAuditTracer(audit_log)
    tracer.log_event("tool_call", tool_name="read_file")
    tracer.log_event("tool_call", tool_name="write_file")
    snap = snapshot([*sources, audit_log], tmp_path / "snapshots")
    _mutate(sources)
    audit_log.write_bytes(audit_log.read_bytes() + b"post-snapshot activity\n")

    rollback(snap, [*sources, audit_log])

    lines = audit_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    record = json.loads(lines[-1])
    assert record["event"] == "rollback"
    assert tracer.verify_integrity()[0] is True


def test_rollback_refuses_unusable_snapshot(tmp_path: Path) -> None:
    sources = _seed_state(tmp_path / "live")
    snap = snapshot(sources, tmp_path / "snapshots")
    digests = _read_table(snap, "digests.json")
    victim = next(iter(sorted(digests)))
    (snap / victim).write_bytes(b"tampered")

    with pytest.raises(SnapshotCorruptError, match="fail verification"):
        rollback(snap, sources)


def test_rollback_pre_snapshot_retries_taken_label(tmp_path: Path) -> None:
    sources = _seed_state(tmp_path / "live")
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)

    first = rollback(snap, sources)
    assert Path(str(first["pre_rollback_snapshot"])) == (
        tmp_path / "snapshots" / "pre-rollback"
    )

    _mutate(sources)
    second = rollback(snap, sources)
    assert Path(str(second["pre_rollback_snapshot"])) == (
        tmp_path / "snapshots" / "pre-rollback-1"
    )
    assert verify_snapshot(Path(str(second["pre_rollback_snapshot"]))) == []


def test_rollback_restores_recorded_modes(tmp_path: Path) -> None:
    sources = _seed_state(tmp_path / "live")
    os.chmod(sources[0], 0o640)
    before = {p: stat.S_IMODE(p.stat().st_mode) for p in sources}
    assert before[sources[0]] == 0o640
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)

    rollback(snap, sources)

    for path in sources:
        assert stat.S_IMODE(path.stat().st_mode) == before[path]


def test_rollback_old_snapshot_without_modes_restores_private(
    tmp_path: Path,
) -> None:
    sources = _seed_state(tmp_path / "live")
    os.chmod(sources[0], 0o644)
    snap = snapshot(sources, tmp_path / "snapshots")
    (snap / "modes.json").unlink()
    _mutate(sources)

    rollback(snap, sources)

    assert stat.S_IMODE(sources[0].stat().st_mode) == 0o600


def test_atomic_restore_fsyncs_parent_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = _seed_state(tmp_path / "live")
    snap = snapshot(sources, tmp_path / "snapshots")
    _mutate(sources)
    real_open = os.open
    opened: list[tuple[str, int]] = []

    def _spy_open(path: str | os.PathLike[str], flags: int, *args: int) -> int:
        opened.append((str(path), flags))
        return real_open(path, flags, *args)

    monkeypatch.setattr(os, "open", _spy_open)
    rollback(snap, sources)

    parents = {str(p.parent) for p in sources}
    assert any(path in parents and flags == os.O_RDONLY for path, flags in opened)


def test_rollback_waits_for_audit_lock(tmp_path: Path) -> None:
    import fcntl

    src = tmp_path / "live"
    sources = _seed_state(src)
    audit_log = src / "grokbot_audit.jsonl"
    tracer = GrokBotAuditTracer(audit_log)
    tracer.log_event("tool_call", tool_name="read_file")
    tracer.log_event("tool_call", tool_name="write_file")
    snap = snapshot([*sources, audit_log], tmp_path / "snapshots")
    _mutate(sources)

    lock_path = audit_log.with_name(audit_log.name + ".lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    locked = threading.Event()
    release = threading.Event()

    def _holder() -> None:
        fcntl.flock(fd, fcntl.LOCK_EX)
        locked.set()
        assert release.wait(timeout=15)
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    holder = threading.Thread(target=_holder, daemon=True)
    holder.start()
    assert locked.wait(timeout=10)

    box: dict[str, object] = {}
    done = threading.Event()

    def _worker() -> None:
        box["result"] = rollback(snap, [*sources, audit_log])
        done.set()

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    time.sleep(0.5)
    assert not done.is_set()
    release.set()
    worker.join(timeout=15)
    holder.join(timeout=15)

    assert done.is_set()
    lines = audit_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert json.loads(lines[-1])["event"] == "rollback"
    assert tracer.verify_integrity()[0] is True


def test_rollback_schema_doc_mentions_modes() -> None:
    import omega_prime.grokbot.rollback as rollback_mod

    assert "modes.json" in (rollback_mod.__doc__ or "")
    assert ".lock" in (rollback_mod.__doc__ or "")
