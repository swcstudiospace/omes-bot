"""Tests for Grok Bot 1-Click Launcher."""

import itertools
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


def _recording_serve(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_serve(**kwargs: Any) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", fake_serve)
    return calls


def test_token_store_reaches_serve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _recording_serve(monkeypatch)
    store = tmp_path / "tokens.json"
    assert (
        main(
            _sse(
                "--host",
                "0.0.0.0",
                "--token-store",
                str(store),
                "--log-format",
                "json",
            )
        )
        == 0
    )
    assert calls[0]["token_store_path"] == store
    assert calls[0]["token"] is None
    assert calls[0]["log_format"] == "json"


def test_token_store_satisfies_bind_safety(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    store = tmp_path / "tokens.json"
    out = tmp_path / "m.json"
    ret = main(
        [
            *_sse("--host", "0.0.0.0", "--token-store", str(store)),
            "--export-manifest",
            str(out),
            "--dry-run",
            "--json",
        ]
    )
    assert ret == 0
    assert not store.exists()
    captured = capsys.readouterr()
    assert "without authentication" not in captured.err
    report = json.loads(captured.out)
    assert report["auth"]["enabled"] is True
    assert report["auth"]["type"] == "bearer"
    assert report["auth"]["source"] == "store"
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["mcp_server"]["auth"]["type"] == "bearer"


def test_token_store_coexists_with_bearer_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _recording_serve(monkeypatch)
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    store = tmp_path / "tokens.json"
    assert main(_sse("--host", "0.0.0.0", "--token-store", str(store))) == 0
    assert calls[0]["token"] == TOKEN
    assert calls[0]["token_store_path"] == store


def test_log_format_is_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _recording_serve(monkeypatch)
    assert main(_sse("--log-format", "json")) == 0
    assert calls[0]["log_format"] == "json"
    assert main(_sse()) == 0
    assert calls[1]["log_format"] == "text"
    assert calls[1]["token_store_path"] is None


def test_self_test_conflicts_with_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--self-test", "--dry-run"]) == 2
    captured = capsys.readouterr()
    assert "dry-run" in captured.err
    assert "omk_" not in captured.out + captured.err


def test_stdio_does_not_forward_sse_only_launcher_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_call(cmd: list[str]) -> int:
        seen.append(cmd)
        return 0

    monkeypatch.setattr(oneclick.subprocess, "call", fake_call)
    store = tmp_path / "tokens.json"
    assert (
        main(["--skip-doctor", "--log-format", "json", "--token-store", str(store)])
        == 0
    )
    assert "--log-format" not in seen[0]
    assert "--token-store" not in seen[0]


_PORT_COUNTER = itertools.count(59000)


def _free_port() -> int:
    """A dummy port number; liveness is scripted so nothing ever binds."""
    return next(_PORT_COUNTER)


def _isolate_supervisor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the default supervisor state at a missing tmp file (never live)."""
    state = tmp_path / "supervisor.json"
    monkeypatch.setattr(
        "omega_prime.grokbot.supervisor._default_state_file", lambda: state
    )


def _sse_launch(
    monkeypatch: pytest.MonkeyPatch,
    out: Path,
    port: int,
    launches: list[Any],
    exit_code: int = 0,
    **kwargs: Any,
) -> int:
    """Run the SSE launcher with a stubbed host; serve kwargs land in launches."""

    def _fake_serve(**serve_kwargs: Any) -> int:
        launches.append(serve_kwargs)
        return exit_code

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", _fake_serve)
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    return run_oneclick(
        find_repo_root(),
        transport="sse",
        port=port,
        export_manifest=out,
        skip_doctor=True,
        **kwargs,
    )


def test_nonzero_exit_records_failed_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A nonzero serve exit records STATUS_FAILED, never complete."""
    from omega_prime.grokbot import receipts

    _isolate_supervisor(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "omega_prime.grokbot.rerun._port_open", lambda host, port: False
    )
    out = tmp_path / "m.json"
    port = _free_port()
    launches: list[Any] = []

    assert _sse_launch(monkeypatch, out, port, launches, exit_code=3) == 3
    receipt_path = receipts.receipt_path_for_manifest(out)
    record = receipts.read_receipt(receipt_path)
    assert record is not None
    assert record["status"] == "failed"
    assert record["exit_code"] == 3
    capsys.readouterr()

    # The failed receipt must not suppress the retry: the next run relaunches
    # and a clean exit completes.
    assert _sse_launch(monkeypatch, out, port, launches, exit_code=0) == 0
    assert len(launches) == 2
    retried = receipts.read_receipt(receipt_path)
    assert retried is not None
    assert retried["status"] == "complete"


def test_json_noop_emits_machine_readable_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Both no-ops keep human text on stderr and emit JSON on stdout."""
    from omega_prime.grokbot import receipts

    _isolate_supervisor(tmp_path, monkeypatch)
    port_open = {"open": False}
    monkeypatch.setattr(
        "omega_prime.grokbot.rerun._port_open",
        lambda host, port: port_open["open"],
    )
    out = tmp_path / "m.json"
    port = _free_port()
    launches: list[Any] = []

    assert _sse_launch(monkeypatch, out, port, launches) == 0
    assert len(launches) == 1
    receipt = receipts.read_receipt(receipts.receipt_path_for_manifest(out))
    assert receipt is not None
    capsys.readouterr()

    assert _sse_launch(monkeypatch, out, port, launches, json_output=True) == 0
    assert len(launches) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "already-complete"
    assert payload["manifest_digest"] == receipt["manifest_digest"]
    assert payload["port"] == port
    assert "already complete" in captured.err

    port_open["open"] = True
    assert _sse_launch(monkeypatch, out, port, launches, json_output=True) == 0
    assert len(launches) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "already-running"
    assert payload["port"] == port
    assert "already running" in captured.err


def test_host_mismatch_does_not_suppress_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A 127.0.0.1 listener must not suppress a launch bound elsewhere."""
    from omega_prime.grokbot import rerun

    _isolate_supervisor(tmp_path, monkeypatch)
    seen: list[str] = []

    def _fake_port_open(host: str, port: int) -> bool:
        seen.append(host)
        return host == "127.0.0.1"

    monkeypatch.setattr("omega_prime.grokbot.rerun._port_open", _fake_port_open)
    out = tmp_path / "m.json"
    port = _free_port()
    launches: list[Any] = []

    assert _sse_launch(monkeypatch, out, port, launches, host="127.0.0.2") == 0
    assert len(launches) == 1
    assert seen and all(host == "127.0.0.2" for host in seen)
    capsys.readouterr()

    # The guard itself is host-scoped: same port, different hosts differ.
    assert rerun.check_rerun(None, port, host="127.0.0.2") == "fresh"
    assert rerun.check_rerun(None, port, host="127.0.0.1") == "already-running"


def test_launch_lock_serializes_check_through_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The per-launch flock covers check_rerun..export, released pre-serve."""
    import contextlib
    from collections.abc import Iterator

    from omega_prime.grokbot import receipts
    from omega_prime.grokbot import rerun as rerun_mod

    _isolate_supervisor(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "omega_prime.grokbot.rerun._port_open", lambda host, port: False
    )
    events: list[str] = []
    real_hold = oneclick._hold_launch_lock

    @contextlib.contextmanager
    def _spy_hold(base: Path) -> Iterator[None]:
        events.append("lock-acquire")
        with real_hold(base):
            events.append("lock-held")
            yield
        events.append("lock-release")

    monkeypatch.setattr(oneclick, "_hold_launch_lock", _spy_hold)

    real_check = rerun_mod.check_rerun

    def _spy_check(*args: Any, **kwargs: Any) -> Any:
        events.append("check")
        return real_check(*args, **kwargs)

    monkeypatch.setattr(rerun_mod, "check_rerun", _spy_check)

    real_write = oneclick.atomic_write_text

    def _spy_write(*args: Any, **kwargs: Any) -> None:
        events.append("export")
        real_write(*args, **kwargs)

    monkeypatch.setattr(oneclick, "atomic_write_text", _spy_write)

    out = tmp_path / "m.json"
    port = _free_port()
    launches: list[Any] = []

    def _fake_serve(**serve_kwargs: Any) -> int:
        events.append("serve")
        launches.append(serve_kwargs)
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", _fake_serve)
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    assert (
        run_oneclick(
            find_repo_root(),
            transport="sse",
            port=port,
            export_manifest=out,
            skip_doctor=True,
        )
        == 0
    )
    capsys.readouterr()
    assert events == [
        "lock-acquire",
        "lock-held",
        "check",
        "export",
        "lock-release",
        "serve",
    ]
    assert len(launches) == 1

    # The sidecar exists and is released: a non-blocking take must succeed.
    receipt_path = receipts.receipt_path_for_manifest(out)
    lock_path = receipt_path.with_name(f"{receipt_path.name}.lock")
    assert lock_path.is_file()
    if oneclick._fcntl is not None:
        fd = os.open(str(lock_path), os.O_RDWR)
        try:
            oneclick._fcntl.flock(fd, oneclick._fcntl.LOCK_EX | oneclick._fcntl.LOCK_NB)
            oneclick._fcntl.flock(fd, oneclick._fcntl.LOCK_UN)
        finally:
            os.close(fd)


def test_no_export_lock_base_is_uid_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The no-export lock base lives in a private per-user dir, not shared tmp."""
    import tempfile

    from omega_prime.grokbot import receipts

    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    port = _free_port()
    base = oneclick._launch_lock_base(None, port)
    assert base.name == f"omega-prime-oneclick-{port}.launch"
    assert base.parent.parent == Path(tempfile.gettempdir())
    assert base.parent.name == f"omega-prime-oneclick-{os.getuid()}"
    assert base.parent.is_dir()
    assert stat.S_IMODE(base.parent.stat().st_mode) & 0o077 == 0

    runtime = tmp_path / "run"
    runtime.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    xdg_base = oneclick._launch_lock_base(None, port)
    assert xdg_base == runtime / f"omega-prime-oneclick-{port}.launch"

    out = tmp_path / "m.json"
    assert oneclick._launch_lock_base(out, port) == receipts.receipt_path_for_manifest(
        out
    )


def test_foreign_owned_lock_file_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A lock file owned by another user warns and proceeds, never raises."""
    base = tmp_path / "omega-prime-oneclick-59999.launch"
    lock_path = base.with_name(f"{base.name}.lock")
    lock_path.write_bytes(b"foreign")
    real_uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real_uid + 1)
    opened: list[str] = []
    real_open = os.open

    def _spy_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(os.fspath(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", _spy_open)
    with oneclick._hold_launch_lock(base):
        pass
    assert opened == []
    assert "proceeding without lock" in capsys.readouterr().err


def test_unusable_lock_file_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A lock file that cannot be opened warns and proceeds, never raises."""
    base = tmp_path / "omega-prime-oneclick-59998.launch"

    def _deny_open(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(os, "open", _deny_open)
    with oneclick._hold_launch_lock(base):
        pass
    assert "proceeding without lock" in capsys.readouterr().err


def test_body_oserror_propagates_without_lock_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A body OSError (e.g. manifest export disk-full) is not a lock error."""
    base = tmp_path / "omega-prime-oneclick-59997.launch"
    with (
        pytest.raises(OSError, match="No space left"),
        oneclick._hold_launch_lock(base),
    ):
        raise OSError(28, "No space left on device")
    assert "proceeding without lock" not in capsys.readouterr().err


def test_foreign_lock_body_oserror_is_not_a_lock_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A body OSError under a foreign-owned lock still propagates as OSError."""
    base = tmp_path / "omega-prime-oneclick-59996.launch"
    base.with_name(f"{base.name}.lock").write_bytes(b"foreign")
    real_uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real_uid + 1)
    with (
        pytest.raises(OSError, match="No space left"),
        oneclick._hold_launch_lock(base),
    ):
        raise OSError(28, "No space left on device")
    err = capsys.readouterr().err
    assert "owned by another user" in err
    assert "cannot use lock" not in err


def test_lock_acquisition_failure_still_runs_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Acquisition failure warns and proceeds: the body still runs."""
    base = tmp_path / "omega-prime-oneclick-59995.launch"

    def _deny_open(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(os, "open", _deny_open)
    ran: list[bool] = []
    with oneclick._hold_launch_lock(base):
        ran.append(True)
    assert ran == [True]
    assert "proceeding without lock" in capsys.readouterr().err


def test_export_oserror_propagates_through_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A manifest-export OSError aborts the launch as OSError, not a lock skip."""
    _isolate_supervisor(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "omega_prime.grokbot.rerun._port_open", lambda host, port: False
    )
    served: list[bool] = []

    def _fake_serve(**serve_kwargs: Any) -> int:
        served.append(True)
        return 0

    monkeypatch.setattr("omega_prime.grokbot.remote.serve_sse", _fake_serve)

    def _deny_write(*args: Any, **kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(oneclick, "atomic_write_text", _deny_write)
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    out = tmp_path / "m.json"
    with pytest.raises(OSError, match="No space left"):
        run_oneclick(
            find_repo_root(),
            transport="sse",
            port=_free_port(),
            export_manifest=out,
            skip_doctor=True,
        )
    assert served == []
    assert "proceeding without lock" not in capsys.readouterr().err


def test_lock_cancel_during_flock_closes_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A cancel while blocked in flock still closes the open descriptor."""
    if oneclick._fcntl is None:
        pytest.skip("flock unavailable on this platform")
    base = tmp_path / "omega-prime-oneclick-59994.launch"
    opened: list[int] = []
    closed: list[int] = []
    real_open = os.open
    real_close = os.close

    def _spy_open(path: Any, *args: Any, **kwargs: Any) -> int:
        fd = real_open(path, *args, **kwargs)
        opened.append(fd)
        return fd

    def _track_close(fd: int, *args: Any, **kwargs: Any) -> None:
        closed.append(fd)
        real_close(fd, *args, **kwargs)

    monkeypatch.setattr(os, "open", _spy_open)
    monkeypatch.setattr(os, "close", _track_close)

    def _raise_cancel(fd: int, op: int) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(oneclick._fcntl, "flock", _raise_cancel)
    ran: list[bool] = []
    with pytest.raises(KeyboardInterrupt), oneclick._hold_launch_lock(base):
        ran.append(True)
    assert ran == []
    assert len(opened) == 1
    assert opened[0] in closed
    with pytest.raises(OSError):
        os.fstat(opened[0])
    assert "proceeding without lock" not in capsys.readouterr().err
