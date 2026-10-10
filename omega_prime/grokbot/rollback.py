# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Snapshot restore (rollback) for the Grok Bot upgrade flow.

Restores live state files from a snapshot created by
:func:`omega_prime.grokbot.upgrade.snapshot`. The snapshot layout and both
tables are consumed exactly as documented in ``upgrade.py`` — this module
defines no second format::

    <dest_dir>/<label>/
        files/              per-source byte-identical copies, each mode 0600
            0000-<basename> copy of the first source path, then 0001-, ...
        sources.json        {stored_rel: original_absolute_path}
        digests.json        {stored_rel: sha256_hex}
        modes.json          {stored_rel: live_st_mode_bits} (absent in old snapshots)

``rollback(snapshot_dir, target_paths, *, dry_run=False)`` restores the
stored copies over the live paths named in ``target_paths`` (absolute file
paths, or a live directory to restore every snapshot entry beneath it).
Each live file is replaced atomically (sibling temp file, fsync,
``os.replace``, then a parent-dir fsync) so a crash never leaves a
half-written state file, then re-hashed against ``digests.json`` and
chmodded to its ``modes.json`` mode (0600 when the snapshot records none).
Before overwriting anything, the current live bytes are preserved with
``upgrade.snapshot`` under the label ``pre-rollback``
(``pre-rollback-<n>`` when that label is taken; snapshots never overwrite).
A taken ``pre-rollback*`` label raises ``upgrade.SnapshotExistsError`` and
is retried under a fresh label; an explicitly-named live path overlapping
the snapshot directory raises ``upgrade.SnapshotOverlapError``, which is
deliberately NOT a ``SnapshotExistsError`` subclass and is never retried
(retrying a caller error under a fresh label could never succeed — it
would loop forever with the audit locks held and nothing restored — so it
propagates and the ``with`` hold below releases the locks).
Audit safety: rollback holds the audit tracer's sidecar lock convention
(exclusive ``flock`` on ``<audit-log>.lock``, same as
:class:`GrokBotAuditTracer`) across the pre-rollback backup and the
replacement writes, so a concurrent auditor cannot append between the
backup read and the replace — those records would otherwise be lost. The
post-restore ``rollback`` record is appended after the hold is released
(via the tracer, which re-locks). On platforms without ``fcntl`` the hold
is a no-op, matching ``audit.py``. When a restored file is an audit log
(its name contains ``audit`` and ends with ``.jsonl``, the repo's
``audit.jsonl`` / ``grokbot_audit.jsonl`` convention), a ``rollback``
record is appended to it via :class:`GrokBotAuditTracer`. With
``dry_run=True`` the planned restores are reported and nothing on disk is
touched.

Secrets are never logged; errors carry paths, never file contents.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

try:
    import fcntl as _fcntl_module

    _fcntl: ModuleType | None = _fcntl_module
except ImportError:  # pragma: no cover - non-POSIX platforms
    _fcntl = None

from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.upgrade import (
    DIGESTS_FILENAME,
    MODES_FILENAME,
    SOURCES_FILENAME,
    SnapshotCorruptError,
    SnapshotExistsError,
    apply_guard,
    snapshot,
)
from omega_prime.tooling.fs import PRIVATE_FILE_MODE, ensure_private_dir

logger = logging.getLogger(__name__)

PRE_ROLLBACK_LABEL = "pre-rollback"
ROLLBACK_EVENT = "rollback"


class RollbackError(Exception):
    """A restore was refused or failed; live state may be partially restored."""


def _read_table(root: Path, name: str) -> dict[str, str]:
    """Parse ``name`` inside ``root`` as a {stored_rel: value} string table."""
    table_path = root / name
    try:
        raw: object = json.loads(table_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotCorruptError(f"snapshot at {root} has no {name}") from exc
    except (OSError, ValueError) as exc:
        raise SnapshotCorruptError(
            f"snapshot at {root} has an unreadable {name}: {exc}"
        ) from exc
    if not isinstance(raw, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, str)
        or Path(key).is_absolute()
        or ".." in Path(key).parts
        for key, value in raw.items()
    ):
        raise SnapshotCorruptError(f"snapshot at {root} has a malformed {name}")
    return dict(raw)


def _read_modes(root: Path) -> dict[str, int]:
    """Parse ``modes.json`` as a {stored_rel: st_mode bits} table.

    Snapshots written before the modes table existed have no file; they
    restore 0600, so a missing file reads as an empty table rather than
    corruption.
    """
    table_path = root / MODES_FILENAME
    if not table_path.exists() and not table_path.is_symlink():
        return {}
    try:
        raw: object = json.loads(table_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotCorruptError(
            f"snapshot at {root} has an unreadable {MODES_FILENAME}: {exc}"
        ) from exc
    if not isinstance(raw, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value <= 0o7777
        or Path(key).is_absolute()
        or ".." in Path(key).parts
        for key, value in raw.items()
    ):
        raise SnapshotCorruptError(
            f"snapshot at {root} has a malformed {MODES_FILENAME}"
        )
    return dict(raw)


@contextlib.contextmanager
def _hold_audit_locks(dests: Iterable[str]) -> Iterator[None]:
    """Hold exclusive sidecar locks for audit-log ``dests``, sorted.

    Same convention as :class:`GrokBotAuditTracer` (exclusive ``flock`` on
    ``<log>.lock``): while held, no auditor can append, so the backup read
    and the replacement writes observe one stable log. A no-op without
    ``fcntl``, matching ``audit.py``.
    """
    targets = sorted({dest for dest in dests if _is_audit_log(dest)})
    held: list[int] = []
    try:
        for dest in targets:
            lock_path = Path(dest).with_name(Path(dest).name + ".lock")
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
            held.append(fd)
        if _fcntl is not None:
            for fd in held:
                _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        if _fcntl is not None:
            for fd in held:
                with contextlib.suppress(OSError):
                    _fcntl.flock(fd, _fcntl.LOCK_UN)
        for fd in held:
            with contextlib.suppress(OSError):
                os.close(fd)


def _plan_restores(
    origins: dict[str, str], target_paths: Iterable[str | Path]
) -> list[tuple[str, str]]:
    """Map each requested target to ``(stored_rel, live_abs_path)`` in order.

    A target naming a live directory selects every snapshot entry recorded
    beneath it. Targets with no snapshot entry raise ``RollbackError`` so a
    typo cannot silently skip a corrupt file. Duplicates collapse to one
    restore per live path.
    """
    by_origin = {os.path.abspath(origin): rel for rel, origin in origins.items()}
    planned: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in target_paths:
        wanted = os.path.abspath(raw)
        hits = [
            (rel, origin)
            for rel, origin in origins.items()
            if os.path.abspath(origin) == wanted
            or os.path.abspath(origin).startswith(wanted + os.sep)
        ]
        if not hits and wanted in by_origin:
            hits = [(by_origin[wanted], wanted)]
        if not hits:
            raise RollbackError(
                f"cannot roll back {wanted}: no entry in snapshot sources.json"
            )
        for rel, origin in sorted(hits):
            dest = os.path.abspath(origin)
            if dest not in seen:
                seen.add(dest)
                planned.append((rel, dest))
    return planned


def _check_stored_copies(
    root: Path, digests: dict[str, str], planned: list[tuple[str, str]]
) -> None:
    """Refuse to restore when a planned stored copy fails its digest."""
    bad = []
    for rel, _dest in planned:
        expected = digests.get(rel)
        try:
            actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        except OSError:
            actual = None
        if expected is None or actual != expected:
            bad.append(rel)
    if bad:
        raise RollbackError(
            f"refusing rollback: snapshot stored copies fail digests.json: "
            f"{', '.join(sorted(bad))}"
        )


def _take_pre_rollback_snapshot(dest_dir: Path, live_paths: list[str]) -> Path:
    """Preserve current live bytes under a fresh ``pre-rollback*`` label.

    Only a taken label (``SnapshotExistsError``) is retried with a fresh
    suffix; ``SnapshotOverlapError`` is not a ``SnapshotExistsError``
    subclass, so an overlapping live path propagates instead of looping.
    """
    label = PRE_ROLLBACK_LABEL
    suffix = 0
    while True:
        try:
            return snapshot(live_paths, dest_dir, label=label)
        except SnapshotExistsError:
            # Label collision only: SnapshotOverlapError is a distinct
            # error type and is deliberately not caught here.
            suffix += 1
            label = f"{PRE_ROLLBACK_LABEL}-{suffix}"


def _atomic_restore(dest: Path, data: bytes, *, mode: int = PRIVATE_FILE_MODE) -> None:
    """Replace ``dest`` with ``data`` (sibling temp file + fsync + rename).

    The temp copy is chmodded to ``mode`` before the rename, then the
    parent directory is fsynced so the rename itself survives a crash
    (mirroring ``omega_prime.tooling.fs.atomic_write_text``; a dir-flush failure is
    suppressed because not every filesystem supports it).
    """
    ensure_private_dir(dest.parent)
    fd, tmp_name = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    with contextlib.suppress(OSError):
        dir_fd = os.open(dest.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


def _is_audit_log(dest: str) -> bool:
    """Whether ``dest`` follows the repo's audit-log naming convention."""
    name = Path(dest).name
    return name.endswith(".jsonl") and "audit" in name


def _append_rollback_record(
    root: Path, restored: list[str], pre_snapshot: Path | None
) -> None:
    """Append a ``rollback`` event to each restored audit log, best effort.

    An audit write failure is logged, never raised: auditing must not turn
    a completed restore into an error (and details carry paths and counts,
    never file contents).
    """
    for dest in restored:
        if not _is_audit_log(dest):
            continue
        try:
            GrokBotAuditTracer(dest).log_event(
                ROLLBACK_EVENT,
                caller="grok-bot",
                details={
                    "snapshot": str(root),
                    "restored": len(restored),
                    "pre_rollback_snapshot": (
                        None if pre_snapshot is None else str(pre_snapshot)
                    ),
                },
            )
        except Exception as exc:
            logger.warning("rollback: audit write failed for %s: %s", dest, exc)


def rollback(
    snapshot_dir: str | Path,
    target_paths: Iterable[str | Path],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Restore ``target_paths`` live files from ``snapshot_dir``.

    Returns ``{"snapshot": ..., "restored": [...], "pre_rollback_snapshot":
    ... | None, "dry_run": ...}`` where ``restored`` lists the absolute
    live paths restored (or planned, for ``dry_run=True``) in order.
    ``dry_run=True`` writes nothing — no restores, no pre-rollback
    snapshot, no audit record, no locks. Otherwise every target parent
    directory is created (0700) before the audit sidecar locks are opened,
    so restoring a file whose parent was deleted still works; the locks are
    then held across the pre-rollback backup and the replacement writes
    (see the module docstring), and each restored file regains its
    ``modes.json`` mode (0600 when unrecorded).
    """
    root = apply_guard(Path(snapshot_dir))
    digests = _read_table(root, DIGESTS_FILENAME)
    origins = _read_table(root, SOURCES_FILENAME)
    modes = _read_modes(root)
    unknown = [rel for rel in origins if rel not in digests]
    if unknown:
        raise SnapshotCorruptError(
            f"snapshot at {root} has sources.json entries "
            f"missing from {DIGESTS_FILENAME}: {', '.join(sorted(unknown))}"
        )
    planned = _plan_restores(origins, target_paths)
    _check_stored_copies(root, digests, planned)
    if dry_run:
        return {
            "snapshot": str(root),
            "restored": [dest for _rel, dest in planned],
            "pre_rollback_snapshot": None,
            "dry_run": True,
        }
    pre_snapshot: Path | None = None
    restored: list[str] = []
    for _rel, dest in planned:
        ensure_private_dir(Path(dest).parent)
    with _hold_audit_locks(dest for _rel, dest in planned):
        live_present = [dest for _rel, dest in planned if Path(dest).is_file()]
        if live_present:
            pre_snapshot = _take_pre_rollback_snapshot(root.parent, live_present)
        for rel, dest in planned:
            _atomic_restore(
                Path(dest),
                (root / rel).read_bytes(),
                mode=modes.get(rel, PRIVATE_FILE_MODE),
            )
            restored.append(dest)
        mismatched = []
        for rel, dest in planned:
            try:
                actual = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
            except OSError:
                actual = None
            if actual != digests[rel]:
                mismatched.append(dest)
        if mismatched:
            raise RollbackError(
                f"rollback from {root} failed digest verification "
                f"for: {', '.join(mismatched)}"
            )
    if restored:
        _append_rollback_record(root, restored, pre_snapshot)
    return {
        "snapshot": str(root),
        "restored": restored,
        "pre_rollback_snapshot": (None if pre_snapshot is None else str(pre_snapshot)),
        "dry_run": False,
    }


__all__ = [
    "PRE_ROLLBACK_LABEL",
    "ROLLBACK_EVENT",
    "RollbackError",
    "rollback",
]
