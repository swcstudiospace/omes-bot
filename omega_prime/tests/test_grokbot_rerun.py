# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for the resume-safe re-run guard."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest

from omega_prime.grokbot import oneclick, receipts, rerun
from omega_prime.grokbot._io import atomic_write_text
from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.oneclick import run_oneclick
from omega_prime.grokbot.security import generate_token

SECRET = "rerun-guard-secret-0123456789-abcdef"


_CLOSED_PORT = 48151
_OPEN_PORT = 48152


def _stub_port(monkeypatch: pytest.MonkeyPatch, *, is_open: bool) -> int:
    """Script the TCP liveness probe; no real network I/O occurs."""
    monkeypatch.setattr(rerun, "_port_open", lambda host, port: is_open)
    return _OPEN_PORT if is_open else _CLOSED_PORT


def _write_receipt(
    tmp_path: Path, name: str, status: str
) -> tuple[Path, dict[str, Any]]:
    record = receipts.build_receipt(
        transport="stdio",
        host="127.0.0.1",
        port=8000,
        manifest={"mcp_server": {"transport": "stdio"}},
        token_source="none",
        doctor_passed=True,
        exit_code=0 if status == "complete" else 130,
        status=status,
    )
    target = tmp_path / name
    receipts.write_receipt(target, record)
    return target, record


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the default supervisor state file at an empty tmp dir."""
    state = tmp_path / "supervisor.json"
    monkeypatch.setattr(
        "omega_prime.grokbot.supervisor._default_state_file", lambda: state
    )
    return state


def test_fresh_when_receipt_missing(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = _stub_port(monkeypatch, is_open=False)
    verdict = rerun.check_rerun(tmp_path / "nope.receipt.json", port)
    assert verdict == "fresh"
    assert verdict.verdict == rerun.VERDICT_FRESH
    assert verdict in rerun.RERUN_VERDICTS


def test_already_complete_carries_digest(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, record = _write_receipt(tmp_path, "m.receipt.json", "complete")
    verdict = rerun.check_rerun(target, _stub_port(monkeypatch, is_open=False))
    assert verdict == "already-complete"
    assert verdict.manifest_digest == record["manifest_digest"]


def test_interrupted(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, _ = _write_receipt(tmp_path, "m.receipt.json", "interrupted")
    verdict = rerun.check_rerun(target, _stub_port(monkeypatch, is_open=False))
    assert verdict == "interrupted"
    assert verdict in rerun.RERUN_VERDICTS


def test_already_running_when_port_open(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = _stub_port(monkeypatch, is_open=True)
    assert rerun.check_rerun(tmp_path / "nope.receipt.json", port) == "already-running"
    target, _ = _write_receipt(tmp_path, "m.receipt.json", "complete")
    assert rerun.check_rerun(target, port) == "already-running"


def test_live_supervisor_means_running(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated_state.write_text(
        json.dumps({"running": True, "supervisor_pid": os.getpid()}),
        encoding="utf-8",
    )
    port = _stub_port(monkeypatch, is_open=False)
    assert rerun.check_rerun(tmp_path / "nope.receipt.json", port) == "already-running"


def test_stale_supervisor_state_does_not_mask_receipt(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated_state.write_text(
        json.dumps({"running": True, "supervisor_pid": 4194303}),
        encoding="utf-8",
    )
    target, _ = _write_receipt(tmp_path, "m.receipt.json", "complete")
    assert rerun.check_rerun(target, _stub_port(monkeypatch, is_open=False)) == (
        "already-complete"
    )


def test_corrupt_receipt_is_fresh_with_warning(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target = tmp_path / "m.receipt.json"
    target.write_text("{not json", encoding="utf-8")
    port = _stub_port(monkeypatch, is_open=False)
    with caplog.at_level(logging.WARNING):
        assert rerun.check_rerun(target, port) == "fresh"
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_check_rerun_has_no_side_effects(
    tmp_path: Path, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, _ = _write_receipt(tmp_path, "m.receipt.json", "complete")
    before = target.read_text(encoding="utf-8")
    port = _stub_port(monkeypatch, is_open=False)
    first = rerun.check_rerun(target, port)
    second = rerun.check_rerun(target, port)
    assert first == second
    assert target.read_text(encoding="utf-8") == before


def _run_stdio(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    out: Path,
    port: int,
    launches: list[list[str]],
    *,
    port_open: bool = False,
    **kwargs: Any,
) -> int:
    def _fake_call(cmd: list[str]) -> int:
        launches.append(cmd)
        return 0

    monkeypatch.setattr(oneclick.subprocess, "call", _fake_call)
    # Script the rerun-guard TCP probe so host state cannot change results.
    monkeypatch.setattr(rerun, "_port_open", lambda host, probe: port_open)
    # Manifest generation needs the real repo tree (roster + seat policy);
    # the manifest output and receipts still live under the tmp root.
    return run_oneclick(
        find_repo_root(),
        transport="stdio",
        port=port,
        export_manifest=out,
        skip_doctor=True,
        **kwargs,
    )


def _run_sse(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    out: Path,
    port: int,
    launches: list[Any],
    *,
    port_open: bool = False,
    **kwargs: Any,
) -> int:
    def _fake_serve(**kw: Any) -> int:
        launches.append(kw)
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", _fake_serve)
    # Script the rerun-guard TCP probe so host state cannot change results.
    monkeypatch.setattr(rerun, "_port_open", lambda host, probe: port_open)
    # SSE serve carries a bearer token: mint one into a 0600 tmp file, the
    # same convention run_self_test uses for its throwaway hosts.
    token_file = root / ".rerun-test-bearer.token"
    if not token_file.is_file():
        atomic_write_text(token_file, generate_token() + "\n")
    # Manifest generation needs the real repo tree (roster + seat policy);
    # the manifest output and receipts still live under the tmp root.
    return run_oneclick(
        find_repo_root(),
        transport="sse",
        port=port,
        export_manifest=out,
        token_file=token_file,
        skip_doctor=True,
        dry_run=False,
        **kwargs,
    )


def test_second_run_is_safe_noop(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "complete")
    receipts.write_receipt(receipt_path, record)
    before = receipt_path.read_text(encoding="utf-8")

    launches: list[Any] = []
    code = _run_sse(monkeypatch, tmp_path, out, _CLOSED_PORT, launches, port_open=False)

    assert code == 0
    assert launches == []
    assert "already complete" in capsys.readouterr().out
    assert receipt_path.read_text(encoding="utf-8") == before


def test_force_bypasses_complete_receipt(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "complete")
    receipts.write_receipt(receipt_path, record)

    launches: list[list[str]] = []
    code = _run_stdio(monkeypatch, tmp_path, out, _CLOSED_PORT, launches, force=True)

    assert code == 0
    assert len(launches) == 1
    assert "nothing to do" not in capsys.readouterr().out


def test_already_running_is_noop_unless_resume(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    out = tmp_path / "m.json"
    launches: list[Any] = []
    code = _run_sse(monkeypatch, tmp_path, out, _OPEN_PORT, launches, port_open=True)
    assert code == 0
    assert launches == []
    assert "already running" in capsys.readouterr().out

    launches.clear()
    code = _run_sse(
        monkeypatch, tmp_path, out, _OPEN_PORT, launches, port_open=True, resume=True
    )
    assert code == 0
    assert len(launches) == 1


def test_interrupted_prints_hint_and_proceeds(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "interrupted")
    receipts.write_receipt(receipt_path, record)

    launches: list[Any] = []
    code = _run_sse(monkeypatch, tmp_path, out, _CLOSED_PORT, launches, port_open=False)

    assert code == 0
    assert len(launches) == 1
    assert "interrupted" in capsys.readouterr().out
    assert receipt_path.is_file()


def test_no_secret_in_guard_messages(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("MCP_AUTH_TOKEN", SECRET)
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "complete")
    receipts.write_receipt(receipt_path, record)

    launches: list[list[str]] = []
    assert _run_stdio(monkeypatch, tmp_path, out, _CLOSED_PORT, launches) == 0
    captured = capsys.readouterr()
    assert SECRET not in captured.out
    assert SECRET not in captured.err
    assert SECRET not in receipt_path.read_text(encoding="utf-8")


def test_main_accepts_force_and_resume(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(oneclick, "run_doctor_checks", lambda *a, **k: {"passed": True})
    assert oneclick.main(["--transport", "stdio", "--dry-run", "--force"]) == 0
    assert oneclick.main(["--transport", "stdio", "--dry-run", "--resume"]) == 0
    capsys.readouterr()


def test_stdio_ignores_occupied_port_and_stale_complete_receipt(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Stdio never uses TCP: a scripted-open probe + stale receipt must not block it."""
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "complete")
    receipts.write_receipt(receipt_path, record)
    launches: list[list[str]] = []
    code = _run_stdio(monkeypatch, tmp_path, out, _OPEN_PORT, launches, port_open=True)
    assert code == 0
    assert len(launches) == 1
    assert "nothing to do" not in capsys.readouterr().out


def test_dry_run_never_noops(
    tmp_path: Path,
    isolated_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Dry-run must always validate and report, never already-complete/no-op."""
    out = tmp_path / "m.json"
    out.write_text('{"mcp_server": {}}', encoding="utf-8")
    receipt_path = receipts.receipt_path_for_manifest(out)
    _, record = _write_receipt(tmp_path, receipt_path.name, "complete")
    receipts.write_receipt(receipt_path, record)
    launches: list[list[str]] = []
    code = _run_stdio(
        monkeypatch, tmp_path, out, _OPEN_PORT, launches, port_open=True, dry_run=True
    )
    assert code == 0
    assert launches == []
    captured = capsys.readouterr()
    assert "Dry run requested" in captured.out
    assert "nothing to do" not in captured.out

    # Script the guard probes for the direct SSE dry-run call too, so host
    # state cannot change the result.
    monkeypatch.setattr(rerun, "_port_open", lambda host, probe: True)
    code = run_oneclick(
        find_repo_root(),
        transport="sse",
        port=_OPEN_PORT,
        export_manifest=out,
        skip_doctor=True,
        dry_run=True,
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Dry run requested" in captured.out
    assert "nothing to do" not in captured.out
