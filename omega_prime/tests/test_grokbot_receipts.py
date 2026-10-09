# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for Grok Bot launch receipts and their 1-Click wiring."""

from __future__ import annotations

import json
import logging
import secrets
import stat
from pathlib import Path
from typing import Any

import pytest

from omega_prime.grokbot import oneclick
from omega_prime.grokbot.manifest import find_repo_root, manifest_digest
from omega_prime.grokbot.receipts import (
    build_receipt,
    read_receipt,
    receipt_path_for_manifest,
    write_receipt,
)

_FAKE_MANIFEST: dict[str, Any] = {"mcp_server": {"transport": "stdio"}, "n": 1}

_SECRETS = [
    "env-" + "token-" + secrets.token_hex(12),
    "argv-" + "token-" + secrets.token_hex(12),
    "sk-" + secrets.token_hex(16),
]


def _record(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "transport": "stdio",
        "host": "127.0.0.1",
        "port": 8000,
        "manifest": _FAKE_MANIFEST,
        "token_source": "env",
        "doctor_passed": True,
        "exit_code": 0,
        "status": "complete",
    }
    fields.update(overrides)
    return build_receipt(**fields)


def test_write_read_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "launch.receipt.json"
    record = _record()
    write_receipt(target, record)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert read_receipt(target) == record


def test_receipt_path_for_manifest_is_a_stable_sibling(tmp_path: Path) -> None:
    manifest_path = tmp_path / "m.json"
    receipt_path = receipt_path_for_manifest(manifest_path)
    assert receipt_path.parent == tmp_path
    assert receipt_path != manifest_path
    assert receipt_path_for_manifest(manifest_path) == receipt_path


def test_receipt_contains_manifest_digest(tmp_path: Path) -> None:
    record = _record()
    assert record["manifest_digest"] == manifest_digest(_FAKE_MANIFEST)
    target = tmp_path / "r.json"
    write_receipt(target, record)
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored["manifest_digest"] == manifest_digest(_FAKE_MANIFEST)


def test_read_receipt_missing_returns_none(tmp_path: Path) -> None:
    assert read_receipt(tmp_path / "nope.json") is None


def test_read_receipt_corrupt_never_raises(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / "r.json"
    target.write_bytes(b"{not json###")
    with caplog.at_level(logging.WARNING, logger="omega_prime.grokbot.receipts"):
        assert read_receipt(target) is None
    assert caplog.records
    target.write_text("[1, 2]", encoding="utf-8")
    assert read_receipt(target) is None


def test_interrupted_status_round_trip(tmp_path: Path) -> None:
    record = _record(status="interrupted", exit_code=130, doctor_passed=False)
    target = tmp_path / "r.json"
    write_receipt(target, record)
    stored = read_receipt(target)
    assert stored is not None
    assert stored["status"] == "interrupted"
    assert stored["exit_code"] == 130
    assert stored["doctor_passed"] is False


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="status"):
        _record(status="running")


@pytest.mark.parametrize("secret", _SECRETS)
def test_token_value_never_in_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, secret: str
) -> None:
    monkeypatch.setenv("MCP_AUTH_TOKEN", secret)
    record = _record(token_source="env")
    assert record["token_source"] == "env"
    assert secret not in json.dumps(record)
    target = tmp_path / "r.json"
    write_receipt(target, record)
    assert secret not in target.read_text(encoding="utf-8")


def test_oneclick_stdio_success_writes_complete_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oneclick.subprocess, "call", lambda cmd: 0)
    out = tmp_path / "m.json"
    ret = oneclick.run_oneclick(
        find_repo_root(), transport="stdio", export_manifest=out, skip_doctor=True
    )
    assert ret == 0
    receipt = read_receipt(receipt_path_for_manifest(out))
    assert receipt is not None
    assert receipt["status"] == "complete"
    assert receipt["exit_code"] == 0
    assert receipt["transport"] == "stdio"
    assert receipt["token_source"] == "none"
    assert receipt["manifest_digest"] == manifest_digest(
        json.loads(out.read_text(encoding="utf-8"))
    )


def test_oneclick_stdio_interrupt_writes_interrupted_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(cmd: list[str]) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(oneclick.subprocess, "call", _boom)
    out = tmp_path / "m.json"
    with pytest.raises(KeyboardInterrupt):
        oneclick.run_oneclick(
            find_repo_root(), transport="stdio", export_manifest=out, skip_doctor=True
        )
    receipt = read_receipt(receipt_path_for_manifest(out))
    assert receipt is not None
    assert receipt["status"] == "interrupted"


def test_oneclick_sse_success_writes_complete_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = _SECRETS[0]
    monkeypatch.setenv("MCP_AUTH_TOKEN", secret)
    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", lambda **kwargs: 0)
    out = tmp_path / "m.json"
    ret = oneclick.run_oneclick(
        find_repo_root(),
        transport="sse",
        host="127.0.0.1",
        port=59129,
        export_manifest=out,
        skip_doctor=True,
    )
    assert ret == 0
    receipt_path = receipt_path_for_manifest(out)
    receipt = read_receipt(receipt_path)
    assert receipt is not None
    assert receipt["status"] == "complete"
    assert receipt["token_source"] == "env"
    assert secret not in receipt_path.read_text(encoding="utf-8")


def test_oneclick_dry_run_writes_no_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _must_not_launch(cmd: list[str]) -> int:
        raise AssertionError("dry run must not launch the host")

    monkeypatch.setattr(oneclick.subprocess, "call", _must_not_launch)
    out = tmp_path / "m.json"
    ret = oneclick.run_oneclick(
        find_repo_root(), transport="stdio", export_manifest=out, dry_run=True
    )
    assert ret == 0
    assert out.is_file()
    assert not receipt_path_for_manifest(out).exists()
