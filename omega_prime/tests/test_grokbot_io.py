# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for the crash-safe file helpers in ``omega_prime.tooling.fs``."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from omega_prime.tooling.fs import (
    atomic_write_json,
    atomic_write_text,
    ensure_private_dir,
    read_secret_file,
)


def test_atomic_write_text_creates_private_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "state.json"
    atomic_write_text(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_atomic_write_replaces_without_leaving_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, "one")
    atomic_write_text(target, "two")
    assert target.read_text(encoding="utf-8") == "two"
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_atomic_write_json_round_trips_sorted(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_json(target, {"b": 1, "a": [1, 2]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": [1, 2], "b": 1}
    assert target.read_text(encoding="utf-8").index('"a"') < target.read_text(
        encoding="utf-8"
    ).index('"b"')


def test_failed_rename_keeps_previous_contents_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, "keep")

    def boom(src: str, dst: str) -> None:
        del src, dst
        raise OSError("disk went away")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="disk went away"):
        atomic_write_text(target, "lost")
    monkeypatch.undo()
    assert target.read_text(encoding="utf-8") == "keep"
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_unserializable_json_never_touches_the_file(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, "keep")
    with pytest.raises(TypeError):
        atomic_write_json(target, {"x": object()})
    assert target.read_text(encoding="utf-8") == "keep"


def test_ensure_private_dir_does_not_loosen_or_tighten_existing(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "shared"
    existing.mkdir(mode=0o755)
    os.chmod(existing, 0o755)
    ensure_private_dir(existing)
    assert stat.S_IMODE(existing.stat().st_mode) == 0o755


def test_read_secret_file_accepts_private_file(tmp_path: Path) -> None:
    secret = tmp_path / "token"
    secret.write_text("  s3cret-value \n", encoding="utf-8")
    os.chmod(secret, 0o600)
    assert read_secret_file(secret) == "s3cret-value"


def test_read_secret_file_rejects_loose_permissions(tmp_path: Path) -> None:
    secret = tmp_path / "token"
    secret.write_text("s3cret", encoding="utf-8")
    os.chmod(secret, 0o644)
    with pytest.raises(ValueError, match="chmod 600"):
        read_secret_file(secret)


def test_read_secret_file_rejects_missing_empty_and_directories(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="cannot read"):
        read_secret_file(tmp_path / "missing")
    empty = tmp_path / "empty"
    empty.write_text("\n", encoding="utf-8")
    os.chmod(empty, 0o600)
    with pytest.raises(ValueError, match="empty"):
        read_secret_file(empty)
    with pytest.raises(ValueError, match="not a regular file"):
        read_secret_file(tmp_path)
