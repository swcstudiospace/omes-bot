# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for pre-upgrade snapshots and the apply guard."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from omega_prime.grokbot.upgrade import (
    SnapshotCorruptError,
    SnapshotExistsError,
    SnapshotMissingError,
    apply_guard,
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
        _write(root / "audit.log", b"line one\nline two\n"),
        _write(root / "manifest.json", b'{"name": "omega-prime"}'),
    ]


def _read_table(snap: Path, name: str) -> dict[str, str]:
    raw: object = json.loads((snap / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return dict(raw)


def test_snapshot_round_trip_digest_match(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)

    snap = snapshot(sources, dest)

    assert snap == dest / "pre-upgrade"
    digests = _read_table(snap, "digests.json")
    assert len(digests) == len(sources)
    for rel, expected in digests.items():
        stored = snap / rel
        assert stored.is_file()
        assert hashlib.sha256(stored.read_bytes()).hexdigest() == expected
        assert stat.S_IMODE(stored.stat().st_mode) == 0o600
    origins = _read_table(snap, "sources.json")
    assert {Path(v) for v in origins.values()} == {
        Path(os.path.abspath(p)) for p in sources
    }
    assert verify_snapshot(snap) == []
    assert apply_guard(snap) == snap


def test_snapshot_tolerates_missing_files(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)
    missing = src / "rotated-out.log"

    snap = snapshot([*sources, missing], dest)

    assert verify_snapshot(snap) == []
    assert len(_read_table(snap, "digests.json")) == len(sources)


def test_snapshot_expands_directories(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)

    snap = snapshot([src], dest)

    assert verify_snapshot(snap) == []
    assert len(_read_table(snap, "digests.json")) == len(sources)


def test_apply_guard_refuses_without_snapshot(tmp_path: Path) -> None:
    missing = tmp_path / "no-snapshot"
    with pytest.raises(SnapshotMissingError, match="no-snapshot"):
        apply_guard(missing)

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SnapshotMissingError, match=r"digests\.json"):
        apply_guard(empty)


def test_apply_guard_refuses_corrupt_table(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    (snap / "digests.json").write_text("not json", encoding="utf-8")
    with pytest.raises(SnapshotCorruptError, match=r"digests\.json"):
        apply_guard(snap)
    with pytest.raises(SnapshotCorruptError, match=r"digests\.json"):
        verify_snapshot(snap)


def test_verify_snapshot_detects_tamper(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    digests = _read_table(snap, "digests.json")
    victim = next(iter(sorted(digests)))
    (snap / victim).write_bytes(b"tampered")

    assert verify_snapshot(snap) == [victim]


def test_snapshot_cleans_temp_dir_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)

    def _boom(self: Path) -> bytes:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "read_bytes", _boom)
    with pytest.raises(OSError, match="No space left"):
        snapshot(sources, dest, label="pre-upgrade")

    assert list(dest.iterdir()) == []
    assert not (dest / "pre-upgrade").exists()


def test_snapshot_never_overwrites(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    snap = snapshot(_seed_state(src), dest)

    with pytest.raises(SnapshotExistsError, match="already exists"):
        snapshot(_seed_state(src), dest)

    assert verify_snapshot(snap) == []


def test_snapshot_rejects_escaping_labels(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)

    for bad in ("", ".", "..", "a/b", "..\\x"):
        with pytest.raises(ValueError, match="plain directory name"):
            snapshot(sources, dest, label=bad)
    assert not dest.exists()


def test_apply_guard_refuses_missing_stored_copy(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    digests = _read_table(snap, "digests.json")
    victim = next(iter(sorted(digests)))
    (snap / victim).unlink()

    with pytest.raises(SnapshotCorruptError, match=r"1 of 4 stored copies fail"):
        apply_guard(snap)


def test_apply_guard_refuses_tampered_stored_copy(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    digests = _read_table(snap, "digests.json")
    victim = next(iter(sorted(digests)))
    (snap / victim).write_bytes(b"tampered")

    with pytest.raises(SnapshotCorruptError, match=r"1 of 4 stored copies fail"):
        apply_guard(snap)


def test_apply_guard_refuses_without_sources(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    (snap / "sources.json").unlink()

    with pytest.raises(SnapshotCorruptError, match=r"sources\.json"):
        apply_guard(snap)


def test_apply_guard_refuses_sources_without_digest(tmp_path: Path) -> None:
    snap = snapshot(_seed_state(tmp_path / "live"), tmp_path / "snapshots")
    sources = _read_table(snap, "sources.json")
    sources["files/9999-rogue"] = os.path.abspath(tmp_path / "live" / "rogue")
    (snap / "sources.json").write_text(json.dumps(sources, sort_keys=True) + "\n")

    with pytest.raises(SnapshotCorruptError, match=r"no digests\.json entry"):
        apply_guard(snap)


def test_snapshot_prunes_dest_dir_subtree(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = src / "backups"
    sources = _seed_state(src)
    _write(dest / "pre-upgrade" / "files" / "0000-stale", b"stale backup")

    snap = snapshot([src], dest, label="fresh")

    origins = _read_table(snap, "sources.json")
    assert len(origins) == len(sources)
    for origin in origins.values():
        assert origin != os.path.abspath(dest)
        assert not origin.startswith(os.path.abspath(dest) + os.sep)


def test_snapshot_publish_race_reports_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)
    final = dest / "pre-upgrade"
    real_replace = os.replace

    def _racing_replace(
        src_path: str | os.PathLike[str], dst_path: str | os.PathLike[str]
    ) -> None:
        if Path(dst_path) == final:
            final.mkdir(parents=True, exist_ok=True)
            (final / "digests.json").write_text("{}\n", encoding="utf-8")
            raise OSError(39, "Directory not empty")
        real_replace(src_path, dst_path)

    monkeypatch.setattr(os, "replace", _racing_replace)
    with pytest.raises(SnapshotExistsError, match="already exists"):
        snapshot(sources, dest)

    assert final.is_dir()
    assert [p.name for p in dest.iterdir()] == ["pre-upgrade"]


def test_snapshot_records_live_modes(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)
    os.chmod(sources[0], 0o640)

    snap = snapshot(sources, dest)

    raw: object = json.loads((snap / "modes.json").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    modes: dict[str, int] = dict(raw)
    origins = _read_table(snap, "sources.json")
    rel = next(rel for rel, origin in origins.items() if Path(origin) == sources[0])
    assert modes[rel] == 0o640
    assert len(modes) == len(sources)


def test_snapshot_schema_doc_mentions_modes() -> None:
    import omega_prime.grokbot.upgrade as upgrade_mod

    assert "modes.json" in (upgrade_mod.__doc__ or "")


def test_snapshot_rejects_explicit_source_under_dest_dir(tmp_path: Path) -> None:
    src = tmp_path / "live"
    dest = tmp_path / "snapshots"
    sources = _seed_state(src)
    inner = _write(dest / "state.json", b'{"v": 1}')

    with pytest.raises(SnapshotExistsError, match="overlaps dest_dir"):
        snapshot([inner], dest, label="explicit-overlap")
    with pytest.raises(SnapshotExistsError, match="overlaps dest_dir"):
        snapshot([*sources, inner], dest, label="mixed-overlap")
    with pytest.raises(SnapshotExistsError, match="overlaps dest_dir"):
        snapshot([dest], dest, label="dest-itself")
    assert not (dest / "explicit-overlap").exists()
    assert not (dest / "mixed-overlap").exists()
    assert not (dest / "dest-itself").exists()


def test_apply_guard_refuses_empty_snapshot(tmp_path: Path) -> None:
    snap = snapshot([tmp_path / "live" / "rotated-away.json"], tmp_path / "snapshots")
    assert _read_table(snap, "digests.json") == {}
    with pytest.raises(SnapshotCorruptError, match="0 entries"):
        apply_guard(snap)
