# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Crash-safe file helpers.

Every writer here replaces a file atomically (write a sibling temp file, fsync,
`os.replace`) so a crash or a concurrent reader never sees a half-written state
file. Files are created private (0600) because they may hold tokens, audit
records, or supervisor state.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

PRIVATE_FILE_MODE = 0o600
PRIVATE_DIR_MODE = 0o700


def ensure_private_dir(path: Path | str, *, mode: int = PRIVATE_DIR_MODE) -> Path:
    """Create `path` (and parents) if missing; only a directory this call creates is chmodded."""
    target = Path(path)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            target.chmod(mode)
    return target


def atomic_write_text(
    path: Path | str,
    data: str,
    *,
    mode: int = PRIVATE_FILE_MODE,
    encoding: str = "utf-8",
) -> None:
    """Atomically replace `path` with `data` (temp file + fsync + rename)."""
    target = Path(path)
    ensure_private_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    # Persist the rename itself; not every filesystem supports fsync on a directory.
    with contextlib.suppress(OSError):
        dir_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


def atomic_write_json(
    path: Path | str,
    obj: Any,
    *,
    mode: int = PRIVATE_FILE_MODE,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> None:
    """Atomically replace `path` with the JSON encoding of `obj`."""
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys)
    atomic_write_text(path, text + "\n", mode=mode)


def read_secret_file(path: Path | str) -> str:
    """Read a one-line secret file. Refuse files other users can read or write.

    Raises `ValueError` for a missing, empty, or group/world-accessible file so a
    misconfigured token file fails closed instead of being silently accepted.
    """
    target = Path(path)
    try:
        info = target.stat()
    except OSError as exc:
        raise ValueError(f"cannot read secret file {target}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"secret file {target} is not a regular file")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError(
            f"secret file {target} is accessible by group/other; run: chmod 600 {target}"
        )
    value = target.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"secret file {target} is empty")
    return value


__all__ = [
    "PRIVATE_DIR_MODE",
    "PRIVATE_FILE_MODE",
    "atomic_write_json",
    "atomic_write_text",
    "ensure_private_dir",
    "read_secret_file",
]
