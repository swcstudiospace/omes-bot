# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Redacted diagnostics bundle collector for the Grok Bot native run.

Assembles a point-in-time support bundle from read-only sources:

* ``doctor`` — :func:`omega_prime.grokbot.doctor.summarize_checks` output.
* ``manifest`` — digest + metadata only. The manifest file itself is never
  embedded because a hand-edited manifest could hold secret material.
* ``supervisor`` — the supervisor ``--status`` state document, read straight
  from the state file (no signals, no restarts).
* ``audit`` — the newest ``N`` audit records (already credential-redacted at
  write time by the audit tracer).
* ``versions`` — ``SERVER_VERSION`` plus the package version.

Everything is serialised to canonical JSON and passed through
:func:`omega_prime.grokbot.secret_guard.assert_no_secrets` *before* any byte
is written. On a leak detection the bundle aborts: no bundle file is created
or replaced (fail-closed).

The collector never mutates the live system: it only reads files and never
probes the host. Doctor output must be injected via ``doctor_checks`` or
``doctor_summary``; when neither is given the doctor section is recorded as
skipped (``{"present": False, "status": "skipped"}``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from omega_prime import __version__ as PACKAGE_VERSION
from omega_prime.grokbot._io import atomic_write_json, ensure_private_dir
from omega_prime.grokbot.audit import GrokBotAuditTracer, default_audit_path
from omega_prime.grokbot.doctor import DiagnosticCheck, summarize_checks
from omega_prime.grokbot.secret_guard import assert_no_secrets
from omega_prime.grokbot.supervisor import _default_state_file

__all__ = [
    "AUDIT_TAIL_LIMIT",
    "BUNDLE_FILENAME",
    "BUNDLE_VERSION",
    "collect_bundle",
]

#: Schema marker written into every bundle.
BUNDLE_VERSION = "1.0.0"

#: File name of the bundle document inside ``out_dir``.
BUNDLE_FILENAME = "diag-bundle.json"

#: Default number of newest audit records embedded in the bundle.
AUDIT_TAIL_LIMIT = 50


def _manifest_section(manifest_path: Path | str | None) -> dict[str, Any]:
    """Digest + metadata for ``manifest_path``; never the file content."""
    if manifest_path is None:
        return {"present": False}
    path = Path(manifest_path)
    try:
        raw = path.read_bytes()
    except OSError:
        return {"present": False, "path": path.name}
    return {
        "present": True,
        "path": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _supervisor_section(state_path: Path | str | None) -> dict[str, Any]:
    """Read-only mirror of ``supervisor --status``: parse the state file.

    No process is signalled and nothing is restarted; a missing or corrupt
    state file is reported as ``present: False`` instead of raising.
    """
    path = Path(state_path) if state_path is not None else _default_state_file()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"present": False, "status": "no_state_file"}
    try:
        data = json.loads(text)
    except ValueError:
        return {"present": False, "status": "unreadable"}
    if not isinstance(data, dict):
        return {"present": False, "status": "unreadable"}
    return {"present": True, "state": data}


def _audit_section(audit_path: Path | str | None, limit: int) -> dict[str, Any]:
    """Newest ``limit`` audit records, oldest first; read-only tail."""
    tracer = GrokBotAuditTracer(
        audit_path if audit_path is not None else default_audit_path(Path.cwd())
    )
    records = tracer.read_recent(limit) if limit > 0 else []
    return {
        "path": tracer.log_path.name,
        "count": len(records),
        "records": records,
    }


def _versions_section() -> dict[str, Any]:
    """Server + package versions without a heavy import at module load.

    ``SERVER_VERSION`` is imported lazily so importing this module never
    loads ``mcp_server``/connectors; an unimportable server reports
    ``{"server": "unavailable"}`` instead of raising.
    """
    try:
        from omega_prime.mcp_server import SERVER_VERSION
    except ImportError:
        return {"server": "unavailable", "package": PACKAGE_VERSION}
    return {"server": SERVER_VERSION, "package": PACKAGE_VERSION}


def _doctor_section(
    doctor_checks: Sequence[DiagnosticCheck] | None,
    doctor_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Doctor summary from injected fixtures; skipped when none are given.

    Never probes the host: with neither ``doctor_summary`` nor
    ``doctor_checks``, records ``{"present": False, "status": "skipped"}``.
    """
    if doctor_summary is not None:
        return dict(doctor_summary)
    if doctor_checks is not None:
        return summarize_checks(doctor_checks)
    return {"present": False, "status": "skipped"}


def collect_bundle(
    out_dir: Path | str,
    *,
    manifest_path: Path | str | None = None,
    audit_path: Path | str | None = None,
    supervisor_state_path: Path | str | None = None,
    doctor_checks: Sequence[DiagnosticCheck] | None = None,
    doctor_summary: Mapping[str, Any] | None = None,
    audit_tail_limit: int = AUDIT_TAIL_LIMIT,
) -> Path:
    """Collect a redacted diagnostics bundle into ``out_dir``.

    All sources are read without mutating the live system and the host is
    never probed: pass ``doctor_checks`` or ``doctor_summary`` for doctor
    output, otherwise the doctor section is recorded as skipped. The
    assembled document is scanned with :func:`assert_no_secrets` before
    any write; a :class:`SecretLeakError` aborts the collection leaving
    any previous bundle file untouched.

    Returns the path of the written ``diag-bundle.json`` file.
    """
    bundle: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "collected_at": datetime.now(UTC).isoformat(),
        "versions": _versions_section(),
        "doctor": _doctor_section(doctor_checks, doctor_summary),
        "manifest": _manifest_section(manifest_path),
        "supervisor": _supervisor_section(supervisor_state_path),
        "audit": _audit_section(audit_path, audit_tail_limit),
    }
    text = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert_no_secrets(text, "diag-bundle")
    target_dir = ensure_private_dir(Path(out_dir))
    target = target_dir / BUNDLE_FILENAME
    atomic_write_json(target, bundle)
    return target
