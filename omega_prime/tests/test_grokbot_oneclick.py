"""Tests for Grok Bot 1-Click Launcher."""

import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest

from omega_prime.grokbot import oneclick
from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.oneclick import main, run_oneclick

TOKEN = "env-token-0123456789-abcdefghijklmnop"


def test_oneclick_dry_run_stdio(tmp_path: Path):
    root = find_repo_root()
    manifest_out = tmp_path / "grok_manifest.json"

    ret = run_oneclick(
        root=root,
        transport="stdio",
        export_manifest=manifest_out,
        dry_run=True,
    )
    assert ret == 0
    assert manifest_out.is_file()

    data = json.loads(manifest_out.read_text(encoding="utf-8"))
    assert data["manifest_version"] == "1.0.0"
    assert data["bot"]["name"] == "Omega Prime"
    assert data["mcp_server"]["transport"] == "stdio"


def test_oneclick_dry_run_sse(tmp_path: Path):
    root = find_repo_root()
    manifest_out = tmp_path / "grok_manifest_sse.json"

    ret = run_oneclick(
        root=root,
        transport="sse",
        host="127.0.0.1",
        port=59125,
        auth_token="test-secret-0123456789",
        export_manifest=manifest_out,
        dry_run=True,
    )
    assert ret == 0
    assert manifest_out.is_file()

    data = json.loads(manifest_out.read_text(encoding="utf-8"))
    assert data["mcp_server"]["transport"] == "sse"
    assert data["mcp_server"]["url"] == "http://127.0.0.1:59125/sse"
    assert data["mcp_server"]["auth"]["type"] == "bearer"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(find_repo_root())  # `--root` defaults to the cwd
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OMEGA_PRIME_TEST_TOKEN", raising=False)


def _doctor_returning(*statuses: str) -> Any:
    """A fake `run_doctor_checks` returning one check per status."""
    seen: list[dict[str, Any]] = []

    def fake(root: Path, port: int, *, host: str, auth_enabled: bool) -> dict[str, Any]:
        del root
        seen.append({"port": port, "host": host, "auth_enabled": auth_enabled})
        checks = [
            {
                "id": f"c{i}",
                "name": f"Check {i}",
                "category": "test",
                "status": status,
                "message": f"{status} message",
                "fix_hint": "do the thing",
            }
            for i, status in enumerate(statuses)
        ]
        return {"passed": "fail" not in statuses, "checks": checks}

    fake.seen = seen  # type: ignore[attr-defined]
    return fake


def _sse(*extra: str) -> list[str]:
    return ["--transport", "sse", "--port", "59125", "--skip-doctor", *extra]


def test_public_url_wins_over_host_and_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    out = tmp_path / "m.json"
    ret = main(
        [
            *_sse("--host", "0.0.0.0"),
            "--public-url",
            "https://bot.example.com/",
            "--export-manifest",
            str(out),
            "--dry-run",
            "--json",
        ]
    )
    assert ret == 0
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["mcp_server"]["url"] == "https://bot.example.com/sse"
    report = json.loads(capsys.readouterr().out)
    assert report["url"] == "https://bot.example.com/sse"


def test_wildcard_host_exports_loopback_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    out = tmp_path / "m.json"
    ret = main([*_sse("--host", "0.0.0.0", "--export-manifest", str(out), "--dry-run")])
    assert ret == 0
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["mcp_server"]["url"] == "http://127.0.0.1:59125/sse"


def test_strict_failure_aborts_with_exit_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    fake = _doctor_returning("ok", "fail")
    monkeypatch.setattr(oneclick, "run_doctor_checks", fake)
    out = tmp_path / "m.json"
    ret = main(
        [
            "--transport",
            "sse",
            "--export-manifest",
            str(out),
            "--dry-run",
            "--json",
        ]
    )
    assert ret == 3
    assert not out.exists()
    captured = capsys.readouterr()
    assert "do the thing" in captured.out + captured.err
    report = json.loads(captured.out)
    assert report["passed"] is False
    assert report["strict"] is True
    assert fake.seen[0]["host"] == "127.0.0.1"
    assert fake.seen[0]["auth_enabled"] is False


def test_no_strict_continues_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setattr(oneclick, "run_doctor_checks", _doctor_returning("fail"))
    out = tmp_path / "m.json"
    ret = main(
        [
            "--transport",
            "sse",
            "--no-strict",
            "--export-manifest",
            str(out),
            "--dry-run",
        ]
    )
    assert ret == 0
    assert out.is_file()
    assert "Continuing launch" in capsys.readouterr().out


def test_warnings_never_abort_and_stdio_defaults_to_non_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(oneclick, "run_doctor_checks", _doctor_returning("warn"))
    assert main(["--transport", "sse", "--dry-run"]) == 0
    monkeypatch.setattr(oneclick, "run_doctor_checks", _doctor_returning("fail"))
    assert main(["--transport", "stdio", "--dry-run"]) == 0
    assert main(["--transport", "stdio", "--strict", "--dry-run"]) == 3


def test_skip_doctor_does_not_call_doctor(monkeypatch: pytest.MonkeyPatch):
    fake = _doctor_returning("fail")
    monkeypatch.setattr(oneclick, "run_doctor_checks", fake)
    assert main(_sse("--dry-run")) == 0
    assert fake.seen == []


@pytest.mark.parametrize("dry_run", [True, False])
def test_bind_safety_refuses_open_wildcard_before_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture, dry_run: bool
):
    out = tmp_path / "m.json"
    argv = _sse("--host", "0.0.0.0", "--export-manifest", str(out))
    if dry_run:
        argv.append("--dry-run")
    assert main(argv) == 2
    assert not out.exists()
    assert "without authentication" in capsys.readouterr().err


def test_allow_insecure_no_auth_permits_wildcard(tmp_path: Path):
    out = tmp_path / "m.json"
    argv = _sse("--host", "0.0.0.0", "--allow-insecure-no-auth")
    ret = main([*argv, "--export-manifest", str(out), "--dry-run"])
    assert ret == 0
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["mcp_server"]["auth"]["type"] == "none"


def test_short_token_is_a_configuration_error(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "short")
    assert main(_sse("--dry-run")) == 2
    assert "too short" in capsys.readouterr().err


def test_token_file_must_be_private(tmp_path: Path, capsys: pytest.CaptureFixture):
    token_file = tmp_path / "token"
    token_file.write_text(TOKEN, encoding="utf-8")
    token_file.chmod(0o644)
    assert main(_sse("--token-file", str(token_file), "--dry-run")) == 2
    assert "chmod 600" in capsys.readouterr().err
    token_file.chmod(0o600)
    assert main(_sse("--token-file", str(token_file), "--dry-run")) == 0


def test_token_env_name_is_configurable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OMEGA_PRIME_TEST_TOKEN", TOKEN)
    out = tmp_path / "m.json"
    ret = main(
        [
            *_sse("--host", "0.0.0.0", "--token-env", "OMEGA_PRIME_TEST_TOKEN"),
            "--export-manifest",
            str(out),
            "--dry-run",
        ]
    )
    assert ret == 0
    auth = json.loads(out.read_text(encoding="utf-8"))["mcp_server"]["auth"]
    assert auth["type"] == "bearer"
    assert auth["token_env"] == "OMEGA_PRIME_TEST_TOKEN"


def test_generate_token_requires_sse(capsys: pytest.CaptureFixture):
    assert main(["--generate-token", "--dry-run"]) == 2
    assert "--transport sse" in capsys.readouterr().err


def test_dry_run_generate_token_neither_prints_nor_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    token_file = tmp_path / "token"
    ret = main(
        [
            *_sse(
                "--host", "0.0.0.0", "--generate-token", "--token-file", str(token_file)
            ),
            "--dry-run",
            "--json",
        ]
    )
    assert ret == 0
    assert not token_file.exists()
    captured = capsys.readouterr()
    assert "omk_" not in captured.out + captured.err
    assert json.loads(captured.out)["auth"]["source"] == "generated"


def test_generate_token_shown_once_and_written_0600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    calls: list[dict[str, Any]] = []
    env_seen: list[str | None] = []

    def fake_serve(**kwargs: Any) -> int:
        calls.append(kwargs)
        env_seen.append(os.environ.get("MCP_AUTH_TOKEN"))
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", fake_serve)
    token_file = tmp_path / "secrets" / "token"
    ret = main(
        [
            *_sse(
                "--host", "0.0.0.0", "--generate-token", "--token-file", str(token_file)
            ),
            "--json",
        ]
    )
    assert ret == 0
    token = token_file.read_text(encoding="utf-8").strip()
    assert token.startswith("omk_")
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600
    captured = capsys.readouterr()
    assert captured.err.count(token) == 1
    assert token not in captured.out
    assert calls[0]["token"] == token
    assert env_seen == [token]
    assert "MCP_AUTH_TOKEN" not in os.environ

    # The saved file is reused: nothing is generated or printed again.
    ret = main(
        _sse("--host", "0.0.0.0", "--generate-token", "--token-file", str(token_file))
    )
    assert ret == 0
    assert calls[1]["token"] == token
    assert token not in capsys.readouterr().err


def test_generate_token_without_file_prints_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    calls: list[dict[str, Any]] = []

    def fake_serve(**kwargs: Any) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", fake_serve)
    assert main(_sse("--generate-token")) == 0
    token = calls[0]["token"]
    captured = capsys.readouterr()
    assert captured.err.count(token) == 1
    assert token not in captured.out


def test_token_never_in_manifest_or_json_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    out = tmp_path / "m.json"
    ret = main(_sse("--export-manifest", str(out), "--dry-run", "--json"))
    assert ret == 0
    assert TOKEN not in out.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert TOKEN not in captured.out
    assert TOKEN not in captured.err
    report = json.loads(captured.out)
    assert set(report) >= {
        "passed",
        "strict",
        "checks",
        "transport",
        "url",
        "manifest_path",
        "auth",
    }
    assert report["manifest_path"] == str(out)
    assert report["auth"]["type"] == "bearer"
    assert stat.S_IMODE(out.stat().st_mode) == 0o644


def test_json_mode_keeps_stdout_machine_readable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setattr(oneclick, "run_doctor_checks", _doctor_returning("ok", "warn"))
    assert main(["--transport", "sse", "--dry-run", "--json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["passed"] is True
    assert [c["status"] for c in report["checks"]] == ["ok", "warn"]
    assert "Preflight Health Checks" in captured.err


def test_argv_token_emits_warning_without_echoing_value(
    capsys: pytest.CaptureFixture,
):
    secret = "argv-token-0123456789-abcdef"
    assert main(_sse("--token", secret, "--dry-run")) == 0
    err = capsys.readouterr().err
    assert "--token" in err
    assert "process" in err
    assert secret not in err


def test_serving_passes_remote_options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []

    def fake_serve(**kwargs: Any) -> int:
        calls.append(kwargs)
        return 7

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", fake_serve)
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    audit_path = tmp_path / "audit.jsonl"
    ret = main(
        [
            *_sse("--public-url", "https://bot.example.com"),
            "--allow-host",
            "bot.example.com",
            "--allow-host",
            "other.example.com",
            "--allow-origin",
            "https://app.example.com",
            "--audit-log",
            str(audit_path),
        ]
    )
    assert ret == 7
    kwargs = calls[0]
    assert kwargs["token"] == TOKEN
    assert kwargs["public_url"] == "https://bot.example.com"
    assert kwargs["allowed_hosts"] == ("bot.example.com", "other.example.com")
    assert kwargs["allowed_origins"] == ("https://app.example.com",)
    assert kwargs["allow_insecure_no_auth"] is False
    assert kwargs["port"] == 59125
    assert Path(kwargs["audit"].log_path) == audit_path


def test_stdio_launch_passes_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seen: list[list[str]] = []

    def fake_call(cmd: list[str]) -> int:
        seen.append(cmd)
        return 0

    monkeypatch.setattr(oneclick.subprocess, "call", fake_call)
    audit_path = tmp_path / "audit.jsonl"
    assert main(["--skip-doctor", "--audit-log", str(audit_path)]) == 0
    assert seen[0][-2:] == ["--audit-log", str(audit_path)]
    assert seen[0][1:3] == ["-m", "omega_prime.mcp_server"]


def test_public_url_must_be_http(capsys: pytest.CaptureFixture):
    assert main(_sse("--public-url", "ftp://nope", "--dry-run")) == 2
    assert "--public-url" in capsys.readouterr().err
