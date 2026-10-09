# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Pre-upgrade snapshots with a guarded apply gate for the Grok Bot runtime.

`snapshot` copies caller-nominated state (state-dir files, token store, audit
log, manifest, ...) into a self-contained snapshot directory and records a
SHA-256 digest table. `apply_guard` refuses to proceed when no snapshot
exists, so an upgrade can never clobber live state without a way back.
`verify_snapshot` re-hashes a snapshot and reports drift. Batch B rollback
restores from exactly the layout and tables described below; keep this
docstring and that consumer in sync.

Snapshot directory layout (``<dest_dir>/<label>/``)::

    <dest_dir>/<label>/
        files/              per-source byte-identical copies, each mode 0600
            0000-<basename> copy of the first source path, then 0001-, ...
        sources.json        {stored_rel: original_absolute_path}
        digests.json        {stored_rel: sha256_hex}
        modes.json          {stored_rel: live_st_mode_bits}

A source that is a directory is expanded recursively (sorted walk); each
regular file inside it gets its own numbered entry. The numeric prefix keeps
entries unique even when sources share a basename, and `sources.json` maps
every stored copy back to the absolute path it came from.

Digest table schema (`digests.json`): a JSON object written via
`_io.atomic_write_json` (sorted keys, trailing newline). Every key is the
POSIX-style path of a stored copy relative to the snapshot root
(`files/NNNN-<basename>`); every value is the lowercase hex SHA-256 of that
stored copy's bytes. The table covers stored copies only and never lists
itself, `sources.json`, or anything outside the snapshot root. Keys that are
absolute or contain `..` are rejected as corrupt.

Sources table schema (`sources.json`): a JSON object written the same way.
Every key is a `digests.json` key; every value is the absolute path of the
source file the copy was read from, so rollback knows where each entry goes.

Modes table schema (`modes.json`): a JSON object written the same way.
Every key is a `digests.json` key; every value is the integer
`stat.S_IMODE` permission bits of the live source file at snapshot time
(e.g. 420 for 0o640), so rollback restores the live mode instead of
forcing 0600. Entries whose mode could not be read are omitted; snapshots
without this table (written before it existed) restore 0600.

Public functions:

- `snapshot(paths, dest_dir, *, label="pre-upgrade") -> Path`: stage the
  copies plus all three tables in a hidden temp dir inside `dest_dir`, then
  publish with one `os.replace` to `dest_dir/<label>/` and return that path.
- `apply_guard(snapshot_dir) -> Path`: return `snapshot_dir` when it holds a
  usable snapshot (readable digest and sources tables, every stored copy
  present with a matching hash), else raise `SnapshotMissingError` naming
  the path or `SnapshotCorruptError` with failure counts.
- `verify_snapshot(snapshot_dir) -> list[str]`: return the sorted stored
  relative paths whose bytes are missing or hash differently than recorded
  (empty means healthy).

Exceptions (`SnapshotError` base): `SnapshotMissingError` (also a
`FileNotFoundError`) for a missing snapshot, `SnapshotCorruptError` for an
unreadable digest table, `SnapshotExistsError` (also a `FileExistsError`)
when the label is already taken.

Guarantees: snapshots never overwrite (re-snapshot under a fresh label); a
publish that loses a label race reports `SnapshotExistsError` (a concurrent
`os.replace` onto an existing label is translated, so pre-rollback retry
works); missing or non-regular sources are skipped, never fatal; a source
directory containing `dest_dir` has the `dest_dir` subtree pruned from the
walk, so snapshots never nest backups inside themselves; symlinks are
followed and stored as regular files; copies are mode 0600 and directories
mode 0700 because sources may hold tokens, while each live source's own
mode bits are recorded in `modes.json` for rollback to restore; any
disk-full or OS error during staging aborts before publish, removes the
temp dir, and leaves any previous snapshot untouched. Pure functions over
paths: no host or CLI wiring here.
Secrets are never logged; error messages carry paths, never file contents.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable
from pathlib import Path

from omega_prime.grokbot._io import (
    PRIVATE_DIR_MODE,
    PRIVATE_FILE_MODE,
    atomic_write_json,
    ensure_private_dir,
)

DIGESTS_FILENAME = "digests.json"
SOURCES_FILENAME = "sources.json"
MODES_FILENAME = "modes.json"
FILES_DIRNAME = "files"
DEFAULT_LABEL = "pre-upgrade"


class SnapshotError(Exception):
    """Base class for snapshot failures; live state is left untouched."""


class SnapshotMissingError(SnapshotError, FileNotFoundError):
    """No usable snapshot exists at the expected path; do not upgrade."""


class SnapshotCorruptError(SnapshotError):
    """A snapshot directory exists but its digest table is unreadable."""


class SnapshotExistsError(SnapshotError, FileExistsError):
    """A snapshot already occupies the label; snapshots never overwrite."""


def _check_label(label: str) -> None:
    """Reject labels that could escape `dest_dir`."""
    if (
        not label
        or label in (".", "..")
        or "/" in label
        or "\\" in label
        or os.path.basename(label) != label
    ):
        raise ValueError(
            f"snapshot label must be a plain directory name, got {label!r}"
        )


def _atomic_write_bytes(
    path: Path, data: bytes, *, mode: int = PRIVATE_FILE_MODE
) -> None:
    """Atomically replace `path` with `data` (temp file + fsync + rename)."""
    ensure_private_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _expand_sources(paths: Iterable[str | Path]) -> list[Path]:
    """Flatten `paths` to regular files; skip missing or special entries."""
    ordered: list[Path] = []
    for raw in paths:
        src = Path(raw)
        if src.is_dir() and not src.is_symlink():
            for root, dirnames, filenames in os.walk(src):
                dirnames.sort()
                for name in sorted(filenames):
                    candidate = Path(root) / name
                    if candidate.is_file():
                        ordered.append(candidate)
        elif src.is_file():
            ordered.append(src)
        # Missing files, broken symlinks, and non-regular files are
        # tolerated: a rotated-out audit log must not fail the snapshot.
    return ordered


def _read_digests(root: Path) -> dict[str, str]:
    """Parse and validate the digest table of the snapshot at `root`."""
    table_path = root / DIGESTS_FILENAME
    try:
        raw: object = json.loads(table_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotMissingError(
            f"refusing upgrade: snapshot at {root} has no {DIGESTS_FILENAME} "
            "(run upgrade.snapshot() first and pass its snapshot directory)"
        ) from exc
    except (OSError, ValueError) as exc:
        raise SnapshotCorruptError(
            f"snapshot at {root} has an unreadable {DIGESTS_FILENAME}: {exc}"
        ) from exc
    if not isinstance(raw, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, str)
        or Path(key).is_absolute()
        or ".." in Path(key).parts
        for key, value in raw.items()
    ):
        raise SnapshotCorruptError(
            f"snapshot at {root} has a malformed {DIGESTS_FILENAME}"
        )
    return dict(raw)


def snapshot(
    paths: Iterable[str | Path],
    dest_dir: str | Path,
    *,
    label: str = DEFAULT_LABEL,
) -> Path:
    """Copy `paths` into `dest_dir/<label>/` with digest tables; return it.

    Missing sources are skipped. An existing label is never overwritten
    (`SnapshotExistsError`); use a fresh label per attempt. A publish that
    loses a concurrent label race (the atomic `os.replace` onto an existing
    label) is translated to `SnapshotExistsError` so callers can retry under
    a fresh label. Sources inside `dest_dir` are pruned, so snapshotting a
    parent of `dest_dir` never nests backups. Each live source's mode bits
    are recorded in `modes.json` for rollback to restore. Any failure
    during staging removes the temp dir and raises, leaving `dest_dir`
    without a partial snapshot.
    """
    _check_label(label)
    dest = ensure_private_dir(Path(dest_dir))
    final = dest / label
    if final.exists() or final.is_symlink():
        raise SnapshotExistsError(f"snapshot {final} already exists; use a fresh label")
    dest_abs = os.path.abspath(dest)
    live = [
        src
        for src in _expand_sources(paths)
        if os.path.abspath(src) != dest_abs
        and not os.path.abspath(src).startswith(dest_abs + os.sep)
    ]
    stage = Path(tempfile.mkdtemp(dir=dest, prefix=f".{label}.stage-"))
    try:
        with contextlib.suppress(OSError):
            os.chmod(stage, PRIVATE_DIR_MODE)
        digests: dict[str, str] = {}
        origins: dict[str, str] = {}
        modes: dict[str, int] = {}
        for index, src in enumerate(live):
            data = src.read_bytes()
            stored_rel = f"{FILES_DIRNAME}/{index:04d}-{src.name}"
            _atomic_write_bytes(stage / stored_rel, data)
            digests[stored_rel] = hashlib.sha256(data).hexdigest()
            origins[stored_rel] = os.path.abspath(src)
            try:
                modes[stored_rel] = stat.S_IMODE(src.stat().st_mode)
            except OSError:
                continue
        atomic_write_json(stage / DIGESTS_FILENAME, digests)
        atomic_write_json(stage / SOURCES_FILENAME, origins)
        atomic_write_json(stage / MODES_FILENAME, modes)
        try:
            os.replace(stage, final)
        except OSError as exc:
            if final.exists() or final.is_symlink():
                raise SnapshotExistsError(
                    f"snapshot {final} already exists; use a fresh label"
                ) from exc
            raise
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    with contextlib.suppress(OSError):
        dir_fd = os.open(dest, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    return final


def _read_sources(root: Path) -> dict[str, str]:
    """Parse and validate the sources table of the snapshot at `root`."""
    table_path = root / SOURCES_FILENAME
    try:
        raw: object = json.loads(table_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotCorruptError(
            f"snapshot at {root} has no {SOURCES_FILENAME} "
            "(run upgrade.snapshot() first and pass its snapshot directory)"
        ) from exc
    except (OSError, ValueError) as exc:
        raise SnapshotCorruptError(
            f"snapshot at {root} has an unreadable {SOURCES_FILENAME}: {exc}"
        ) from exc
    if not isinstance(raw, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, str)
        or Path(key).is_absolute()
        or ".." in Path(key).parts
        for key, value in raw.items()
    ):
        raise SnapshotCorruptError(
            f"snapshot at {root} has a malformed {SOURCES_FILENAME}"
        )
    return dict(raw)


def apply_guard(snapshot_dir: str | Path) -> Path:
    """Return `snapshot_dir` when it holds a usable snapshot.

    Raise `SnapshotMissingError` (naming the path) when no snapshot exists,
    or `SnapshotCorruptError` (with failure counts) when the digest or
    sources table is unreadable, a sources entry has no digest, or any
    stored copy is missing or hashes differently than recorded. Call this
    before any upgrade step that overwrites live state.
    """
    root = Path(snapshot_dir)
    if not root.is_dir():
        raise SnapshotMissingError(
            f"refusing upgrade: no snapshot at {root} "
            "(run upgrade.snapshot() first and pass its snapshot directory)"
        )
    digests = _read_digests(root)
    sources = _read_sources(root)
    unknown = [rel for rel in sources if rel not in digests]
    if unknown:
        raise SnapshotCorruptError(
            f"snapshot at {root} is unusable: {len(unknown)} of "
            f"{len(sources)} sources entries have no {DIGESTS_FILENAME} "
            f"entry: {', '.join(sorted(unknown))}"
        )
    bad = verify_snapshot(root)
    if bad:
        raise SnapshotCorruptError(
            f"snapshot at {root} is unusable: {len(bad)} of {len(digests)} "
            f"stored copies fail verification: {', '.join(bad)}"
        )
    return root


def verify_snapshot(snapshot_dir: str | Path) -> list[str]:
    """Re-hash a snapshot; return sorted stored paths that fail to verify.

    An empty list means every stored copy matches its recorded digest.
    Missing stored copies count as failures.
    """
    root = Path(snapshot_dir)
    if not root.is_dir():
        raise SnapshotMissingError(
            f"refusing upgrade: no snapshot at {root} "
            "(run upgrade.snapshot() first and pass its snapshot directory)"
        )
    digests = _read_digests(root)
    bad: list[str] = []
    for rel, expected in digests.items():
        try:
            actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        except OSError:
            bad.append(rel)
            continue
        if actual != expected:
            bad.append(rel)
    return sorted(bad)


__all__ = [
    "DEFAULT_LABEL",
    "DIGESTS_FILENAME",
    "FILES_DIRNAME",
    "MODES_FILENAME",
    "SOURCES_FILENAME",
    "SnapshotCorruptError",
    "SnapshotError",
    "SnapshotExistsError",
    "SnapshotMissingError",
    "apply_guard",
    "snapshot",
    "verify_snapshot",
]
