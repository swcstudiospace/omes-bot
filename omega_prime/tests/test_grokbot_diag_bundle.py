# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for the redacted Grok Bot diagnostics bundle collector."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from omega_prime import __version__ as PACKAGE_VERSION
from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.diag_bundle import BUNDLE_FILENAME, collect_bundle
from omega_prime.grokbot.doctor import DiagnosticCheck
from omega_prime.grokbot.secret_guard import SecretLeakError
from omega_prime.mcp_server import SERVER_VERSION

_OMK_TOKEN = "omk-a1b2c3d4e5f6g7h8ij"
_MANIFEST_MARKER = "grokbot-fixture-marker-7f3a"


def _checks() -> list[DiagnosticCheck]:
    return [
        DiagnosticCheck(
            id="python_version",
            category="env",
            title="Python version",
            status="PASS",
            message="ok",
        )
    ]


def _manifest_file(tmp_path: Path) -> Path:
    target = tmp_path / "manifest.json"
    target.write_text(
        json.dumps({"name": _MANIFEST_MARKER, "version": "1.0.0"}),
        encoding="utf-8",
    )
    return target


def _supervisor_state(tmp_path: Path, *, last_error: str | None = None) -> Path:
    target = tmp_path / "supervisor.json"
    target.write_text(
        json.dumps(
            {
                "running": False,
                "pid": None,
                "restarts": 0,
                "uptime_seconds": 0.0,
                "last_exit_code": None,
                "last_error": last_error,
            }
        ),
        encoding="utf-8",
    )
    return target


def _audit_log(tmp_path: Path) -> Path:
    target = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(target)
    tracer.log_event("tool_call", tool_name="todo_read", details={"args": "clean"})
    tracer.log_event("tool_call", tool_name="todo_read", details={"args": "clean"})
    return target


def _collect(tmp_path: Path, **kwargs) -> Path:
    return collect_bundle(
        tmp_path / "bundle",
        manifest_path=kwargs.get("manifest_path", _manifest_file(tmp_path)),
        audit_path=kwargs.get("audit_path", _audit_log(tmp_path)),
        supervisor_state_path=kwargs.get(
            "supervisor_state_path", _supervisor_state(tmp_path)
        ),
        doctor_checks=kwargs.get("doctor_checks", _checks()),
    )


def test_bundle_assembles_from_fixtures(tmp_path: Path):
    out = _collect(tmp_path)
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["doctor"]["passed"] is True
    assert bundle["manifest"]["present"] is True
    assert bundle["supervisor"]["present"] is True
    assert bundle["supervisor"]["state"]["restarts"] == 0
    assert bundle["audit"]["count"] == 2


def test_secret_bearing_fixture_aborts_without_writing(tmp_path: Path):
    out_dir = tmp_path / "bundle"
    with pytest.raises(SecretLeakError):
        collect_bundle(
            out_dir,
            manifest_path=_manifest_file(tmp_path),
            audit_path=_audit_log(tmp_path),
            supervisor_state_path=_supervisor_state(tmp_path, last_error=_OMK_TOKEN),
            doctor_checks=_checks(),
        )
    assert not (out_dir / BUNDLE_FILENAME).exists()


def test_output_contains_versions_and_digests(tmp_path: Path):
    manifest = _manifest_file(tmp_path)
    raw = manifest.read_bytes()
    out = _collect(tmp_path, manifest_path=manifest)
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["versions"] == {"server": SERVER_VERSION, "package": PACKAGE_VERSION}
    assert bundle["manifest"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert bundle["manifest"]["size_bytes"] == len(raw)
    # Digest + metadata only: the manifest content itself is never embedded.
    assert "content" not in bundle["manifest"]
    assert _MANIFEST_MARKER not in out.read_text(encoding="utf-8")


def test_no_token_bytes_in_bundle_dir(tmp_path: Path):
    out = _collect(tmp_path)
    for entry in out.parent.iterdir():
        if entry.is_file():
            assert _OMK_TOKEN.encode() not in entry.read_bytes()
            assert b"omk-" not in entry.read_bytes()
