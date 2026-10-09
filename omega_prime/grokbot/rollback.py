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

``rollback(snapshot_dir, target_paths, *, dry_run=False)`` restores the
stored copies over the live paths named in ``target_paths`` (absolute file
paths, or a live directory to restore every snapshot entry beneath it).
Each live file is replaced atomically (sibling temp file, fsync,
``os.replace``) so a crash never leaves a half-written state file, then
re-hashed against ``digests.json``. Before overwriting anything, the
current live bytes are preserved with ``upgrade.snapshot`` under the label
``pre-rollback`` (``pre-rollback-<n>`` when that label is taken; snapshots
never overwrite). When a restored file is an audit log (its name contains
``audit`` and ends with ``.jsonl``, the repo's ``audit.jsonl`` /
``grokbot_audit.jsonl`` convention), a ``rollback`` record is appended to
it via :class:`GrokBotAuditTracer`. With ``dry_run=True`` the planned
restores are reported and nothing on disk is touched.

Secrets are never logged; errors carry paths, never file contents.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from omega_prime.grokbot._io import PRIVATE_FILE_MODE, ensure_private_dir
from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.upgrade import (
    DIGESTS_FILENAME,
    SOURCES_FILENAME,
    SnapshotCorruptError,
    SnapshotExistsError,
    apply_guard,
    snapshot,
)

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
    """Preserve current live bytes under a fresh ``pre-rollback*`` label."""
    label = PRE_ROLLBACK_LABEL
    suffix = 0
    while True:
        try:
            return snapshot(live_paths, dest_dir, label=label)
        except SnapshotExistsError:
            suffix += 1
            label = f"{PRE_ROLLBACK_LABEL}-{suffix}"


def _atomic_restore(dest: Path, data: bytes) -> None:
    """Replace ``dest`` with ``data`` (sibling temp file + fsync + rename)."""
    ensure_private_dir(dest.parent)
    fd, tmp_name = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, PRIVATE_FILE_MODE)
        os.replace(tmp_name, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


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
    snapshot, no audit record.
    """
    root = apply_guard(Path(snapshot_dir))
    digests = _read_table(root, DIGESTS_FILENAME)
    origins = _read_table(root, SOURCES_FILENAME)
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
    live_present = [dest for _rel, dest in planned if Path(dest).is_file()]
    if live_present:
        pre_snapshot = _take_pre_rollback_snapshot(root.parent, live_present)
    restored: list[str] = []
    for rel, dest in planned:
        _atomic_restore(Path(dest), (root / rel).read_bytes())
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
