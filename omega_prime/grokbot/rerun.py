# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Resume-safe re-run guard for the Grok Bot 1-Click launcher.

:class:`check_rerun` classifies a launch attempt as one of ``fresh``,
``already-complete``, ``already-running`` or ``interrupted``. It is a pure
function: it never writes, deletes, or otherwise mutates state.
"""

from __future__ import annotations

import logging
import socket
from pathlib import Path
from typing import Any

from omega_prime.grokbot import receipts as _receipts
from omega_prime.grokbot import supervisor as _supervisor

logger = logging.getLogger(__name__)

VERDICT_FRESH = "fresh"
VERDICT_ALREADY_COMPLETE = "already-complete"
VERDICT_ALREADY_RUNNING = "already-running"
VERDICT_INTERRUPTED = "interrupted"

RERUN_VERDICTS = frozenset(
    {
        VERDICT_FRESH,
        VERDICT_ALREADY_COMPLETE,
        VERDICT_ALREADY_RUNNING,
        VERDICT_INTERRUPTED,
    }
)


class RerunVerdict(str):
    """A verdict string carrying the receipt's manifest digest, if any.

    Behaves exactly like the plain verdict string (equality, hashing and
    ``in`` checks against ``RERUN_VERDICTS`` all work) while exposing the
    ``manifest_digest`` and ``verdict`` attributes for callers that need
    the digest for their message.
    """

    manifest_digest: str | None
    verdict: str

    def __new__(cls, verdict: str, digest: str | None = None) -> RerunVerdict:
        obj = super().__new__(cls, verdict)
        obj.manifest_digest = digest
        obj.verdict = str(verdict)
        return obj


def _port_open(host: str, port: int) -> bool:
    """True when a TCP connect to ``host:port`` succeeds."""
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _supervisor_live(state_path: Path | str | None) -> bool:
    """True when the supervisor state file names a live process."""
    path = (
        Path(state_path)
        if state_path is not None
        else _supervisor._default_state_file()
    )
    try:
        data = _supervisor._read_state(path)
    except ValueError as exc:
        logger.warning("ignoring unreadable supervisor state %s: %s", path, exc)
        return False
    except OSError as exc:
        logger.warning("ignoring unreadable supervisor state %s: %s", path, exc)
        return False
    if not isinstance(data, dict):
        return False
    candidates: list[Any] = [
        data.get("supervisor_pid"),
        data.get("child_pid"),
        data.get("pid"),
    ]
    for pid in candidates:
        if isinstance(pid, int) and not isinstance(pid, bool) and pid > 1:
            try:
                if _supervisor._pid_alive(pid):
                    return True
            except Exception as exc:  # never let liveness probing raise
                logger.warning("supervisor liveness probe failed: %s", exc)
                return False
    return False


def check_rerun(
    receipt_path: Path | str | None,
    port: int,
    *,
    state_path: Path | str | None = None,
    host: str = "127.0.0.1",
) -> RerunVerdict:
    """Classify a launch attempt without side effects.

    Liveness (a live supervisor process or an open TCP ``port``) wins over
    any receipt: a live host must never be double-spawned. Otherwise the
    receipt decides: missing or corrupt means ``fresh``, ``complete`` means
    ``already-complete`` (carrying the manifest digest), ``interrupted``
    means ``interrupted``. Unknown receipt shapes fall back to ``fresh``.
    """
    if _supervisor_live(state_path) or _port_open(host, port):
        return RerunVerdict(VERDICT_ALREADY_RUNNING)
    if receipt_path is None:
        return RerunVerdict(VERDICT_FRESH)
    target = Path(receipt_path)
    receipt = _receipts.read_receipt(target)
    if receipt is None:
        if target.is_file():
            logger.warning(
                "ignoring corrupt launch receipt %s; treating as fresh", target
            )
        return RerunVerdict(VERDICT_FRESH)
    status = receipt.get("status")
    digest = receipt.get("manifest_digest")
    if status == _receipts.STATUS_COMPLETE:
        return RerunVerdict(
            VERDICT_ALREADY_COMPLETE, digest if isinstance(digest, str) else None
        )
    if status == _receipts.STATUS_INTERRUPTED:
        return RerunVerdict(
            VERDICT_INTERRUPTED, digest if isinstance(digest, str) else None
        )
    return RerunVerdict(VERDICT_FRESH)


__all__ = [
    "RERUN_VERDICTS",
    "VERDICT_ALREADY_COMPLETE",
    "VERDICT_ALREADY_RUNNING",
    "VERDICT_FRESH",
    "VERDICT_INTERRUPTED",
    "RerunVerdict",
    "check_rerun",
]
