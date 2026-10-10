# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Idempotent launch receipts for the Grok Bot 1-Click launcher.

A receipt records one launcher run so a later run (or an operator) can tell
what was exported or served without ever touching a secret:

* ``write_receipt(path, record)`` atomically replaces ``path`` with the JSON
  encoding of ``record`` (via :func:`omega_prime.tooling.fs.atomic_write_text`,
  mode ``0600``). Use it after a manifest was actually exported or a host was
  served; never on the ``--dry-run`` path.
* ``read_receipt(path)`` returns the stored mapping, or ``None`` when ``path``
  is missing or corrupt. A corrupt file logs a warning and never raises, so
  callers can proceed with a fresh launch.
* ``build_receipt(...)`` builds a record with exactly the supported fields:
  ``entrypoint``, ``python_version``, ``transport``, ``host``, ``port``,
  ``manifest_digest`` (computed with
  :func:`omega_prime.grokbot.manifest.manifest_digest`), ``token_source``
  (the source *name* such as ``"env"`` — never the secret itself),
  ``doctor_passed``, ``exit_code``, and ``status`` (``"complete"`` or
  ``"interrupted"``).
* ``receipt_path_for_manifest(manifest_path)`` maps an exported manifest path
  to its sibling receipt path (``<stem>.receipt.json``), so repeated launches
  with the same ``--export-manifest`` overwrite the same receipt.
"""

from __future__ import annotations

import json
import logging
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from omega_prime.grokbot.manifest import manifest_digest
from omega_prime.tooling.fs import PRIVATE_FILE_MODE, atomic_write_text

logger = logging.getLogger(__name__)

ENTRYPOINT_ONECLICK = "omega-prime-grokbot-oneclick"

STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"
STATUS_INTERRUPTED = "interrupted"
RECEIPT_STATUSES = frozenset({STATUS_COMPLETE, STATUS_FAILED, STATUS_INTERRUPTED})


def build_receipt(
    *,
    transport: str,
    host: str,
    port: int,
    manifest: Mapping[str, Any] | None = None,
    manifest_digest_value: str | None = None,
    token_source: str,
    doctor_passed: bool | None,
    exit_code: int,
    status: str,
    entrypoint: str = ENTRYPOINT_ONECLICK,
    python_version: str | None = None,
) -> dict[str, Any]:
    """Build a launch receipt record.

    The digest comes from ``manifest`` via :func:`manifest_digest` when a
    manifest mapping is given, otherwise from ``manifest_digest_value``. One
    of the two is required. ``token_source`` is the source *name* (``"env"``,
    ``"file"``, ``"argv"``, ``"generated"``, ``"store"``, ``"none"``) — the
    secret value must never be passed here. Raises ``ValueError`` for an
    unknown ``status`` or a missing digest.
    """
    if status not in RECEIPT_STATUSES:
        raise ValueError(f"unknown receipt status: {status!r}")
    if manifest is not None:
        digest = manifest_digest(manifest)
    elif manifest_digest_value is not None:
        digest = manifest_digest_value
    else:
        raise ValueError("build_receipt requires manifest or manifest_digest_value")
    return {
        "entrypoint": entrypoint,
        "python_version": python_version or platform.python_version(),
        "transport": transport,
        "host": host,
        "port": port,
        "manifest_digest": digest,
        "token_source": token_source,
        "doctor_passed": doctor_passed,
        "exit_code": exit_code,
        "status": status,
    }


def receipt_path_for_manifest(manifest_path: Path | str) -> Path:
    """Return the sibling receipt path for an exported manifest path."""
    target = Path(manifest_path)
    return target.parent / f"{target.stem}.receipt.json"


def write_receipt(path: Path | str, record: Mapping[str, Any]) -> None:
    """Atomically write ``record`` as sorted JSON to ``path`` (mode 0600)."""
    text = json.dumps(dict(record), indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, text, mode=PRIVATE_FILE_MODE)


def read_receipt(path: Path | str) -> dict[str, Any] | None:
    """Return the receipt mapping at ``path``, or ``None`` when missing/corrupt.

    A missing file returns ``None`` silently; an unreadable or corrupt file
    logs a warning and returns ``None``. Never raises for those cases so the
    launcher can proceed with a fresh run.
    """
    target = Path(path)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("ignoring corrupt launch receipt %s: %s", target, exc)
        return None
    if not isinstance(data, dict):
        logger.warning("ignoring corrupt launch receipt %s: not a JSON object", target)
        return None
    return data


__all__ = [
    "ENTRYPOINT_ONECLICK",
    "RECEIPT_STATUSES",
    "STATUS_COMPLETE",
    "STATUS_FAILED",
    "STATUS_INTERRUPTED",
    "build_receipt",
    "read_receipt",
    "receipt_path_for_manifest",
    "write_receipt",
]
