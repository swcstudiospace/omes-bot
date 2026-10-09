# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Black-box conformance verifier against a real host and hostile wrappers."""

from __future__ import annotations

import contextlib
import json
import socket
import subprocess
import sys
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.tokens import create_token
from omega_prime.grokbot.verify import (
    Check,
    VerifyReport,
    format_report,
    main,
    run_verification,
)
from omega_prime.tests.test_grokbot_integration import _app, _serve

_TRACE = {
    "X-Request-Id": "0123456789abcdef",
    "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
}
_WWW = {"WWW-Authenticate": 'Bearer realm="omega-prime"'}
_EXPECTED = [
    "health",
    "ready",
    "auth_required",
    "auth_missing",
    "auth_query_token",
    "auth_invalid",
    "origin_rejected",
    "request_id",
    "manifest",
    "metrics",
    "sse:initialize",
    "sse:list_tools",
    "sse:call_tool",
    "sse:unknown_tool",
    "sse:gated_tool_refused",
    "http:initialize",
    "http:list_tools",
    "http:call_tool",
    "http:unknown_tool",
    "http:gated_tool_refused",
    "admin:scope_enforced",
    "admin:approval_roundtrip",
]
_Handler = Callable[[Request], Awaitable[Response]]


def _check(report: VerifyReport, check_id: str) -> Check:
    for item in report.checks:
        if item.id == check_id:
            return item
    raise AssertionError(check_id)


def _write_secret(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)


def _closed_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _health_body(auth: str, rostered: int) -> dict[str, object]:
    return {
        "status": "healthy",
        "service": "wrapper",
        "version": "test",
        "rostered_tools": rostered,
        "auth": auth,
    }


@contextlib.contextmanager
def _wrapper(handler: _Handler) -> Iterator[str]:
    app = Starlette(
        routes=[
            Route("/{path:path}", handler, methods=["GET", "POST", "DELETE"]),
        ]
    )
    with _serve(app) as host:
        yield host.base


def test_integrated_host_passes_every_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = tmp_path / "tokens.json"
    caller, _caller_record = create_token(
        store, scopes=["read", "call"], label="caller"
    )
    admin, _admin_record = create_token(store, scopes=["admin"], label="ops")
    caller_file = tmp_path / "caller"
    admin_file = tmp_path / "admin"
    _write_secret(caller_file, caller)
    _write_secret(admin_file, admin)
    app = _app(tmp_path, token_store_path=store)
    with _serve(app) as host:
        report = run_verification(
            host.base,
            token=caller,
            admin_token=admin,
            require_auth=True,
            timeout=15,
        )
        code = main(
            [
                "--url",
                host.base,
                "--token-file",
                str(caller_file),
                "--admin-token-file",
                str(admin_file),
                "--require-auth",
                "--timeout",
                "15",
                "--json",
            ]
        )
        captured = capsys.readouterr()
    failed = [(item.id, item.detail) for item in report.checks if item.status != "pass"]
    assert not failed
    assert [item.id for item in report.checks] == _EXPECTED
    assert report.ok is True
    assert report.server_version
    payload = report.to_dict()
    assert set(payload) == {"ok", "base_url", "server_version", "counts", "checks"}
    assert payload["counts"] == {"pass": len(_EXPECTED), "fail": 0, "skip": 0}
    assert set(payload["checks"][0]) == {
        "id",
        "title",
        "status",
        "detail",
        "duration_ms",
    }
    rendered = format_report(report)
    blob = json.dumps(payload) + rendered + captured.out + captured.err
    assert caller not in blob
    assert admin not in blob
    assert code == 0
    cli = json.loads(captured.out)
    assert cli["ok"] is True
    assert cli["counts"]["fail"] == 0
    assert [item["id"] for item in cli["checks"]] == _EXPECTED


def test_auth_disabled_fails_only_when_required(tmp_path: Path) -> None:
    del tmp_path

    async def handler(request: Request) -> Response:
        if request.url.path == "/healthz":
            return JSONResponse(_health_body("disabled", 0), headers=_TRACE)
        if request.url.path == "/readyz":
            return JSONResponse({"ready": True})
        return JSONResponse({"error": "unauthorized"}, status_code=401, headers=_WWW)

    with _wrapper(handler) as base:
        skipped = run_verification(base, timeout=2)
        failed = run_verification(base, timeout=2, require_auth=True)
    assert _check(skipped, "auth_required").status == "skip"
    assert _check(failed, "auth_required").status == "fail"
    assert failed.ok is False
    assert all(not item.id.startswith("admin:") for item in skipped.checks)


def test_query_token_accepted_is_a_failure() -> None:
    token = "omk_query_probe_token_0123456789abcd"

    async def handler(request: Request) -> Response:
        if request.query_params.get("token"):
            return JSONResponse({"accepted": True})
        if request.url.path == "/healthz":
            return JSONResponse(_health_body("required", 0), headers=_TRACE)
        if request.url.path == "/readyz":
            return JSONResponse({"ready": True})
        return JSONResponse({"error": "unauthorized"}, status_code=401, headers=_WWW)

    with _wrapper(handler) as base:
        report = run_verification(base, token=token, timeout=2)
    assert _check(report, "auth_query_token").status == "fail"
    assert report.ok is False
    assert token not in json.dumps(report.to_dict())
    assert token not in format_report(report)


def test_lying_manifest_fails_and_cli_exits_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def handler(request: Request) -> Response:
        if request.url.path == "/healthz":
            return JSONResponse(_health_body("disabled", 4), headers=_TRACE)
        if request.url.path == "/readyz":
            return JSONResponse({"ready": True})
        if request.url.path == "/manifest.json":
            return JSONResponse(
                {
                    "digest": "abc",
                    "mcp_server": {
                        "tools": ["only"],
                        "rostered_tool_count": 1,
                        "approval_required": [],
                    },
                }
            )
        return JSONResponse({"error": "no"}, status_code=404)

    with _wrapper(handler) as base:
        report = run_verification(base, timeout=2)
        code = main(["--url", base, "--timeout", "2", "--json"])
        captured = capsys.readouterr()
    assert _check(report, "manifest").status == "fail"
    assert "tool count" in _check(report, "manifest").detail
    assert report.ok is False
    assert code == 1
    body = json.loads(captured.out)
    assert body["ok"] is False
    assert body["counts"]["fail"] >= 1


def test_manifest_that_echoes_the_token_is_redacted() -> None:
    token = "omk_manifest_leak_0123456789abcdef"

    async def handler(request: Request) -> Response:
        if request.url.path == "/healthz":
            return JSONResponse(_health_body("required", 0), headers=_TRACE)
        if request.url.path == "/manifest.json":
            return JSONResponse(
                {
                    "digest": token,
                    "leak": token,
                    "mcp_server": {
                        "tools": [],
                        "rostered_tool_count": 0,
                        "approval_required": [],
                    },
                }
            )
        return JSONResponse({"error": "unauthorized"}, status_code=401, headers=_WWW)

    with _wrapper(handler) as base:
        report = run_verification(base, token=token, timeout=2)
    check = _check(report, "manifest")
    assert check.status == "fail"
    assert token not in check.detail
    assert token not in json.dumps(report.to_dict())
    assert token not in format_report(report)


def test_missing_request_id_fails() -> None:
    async def handler(request: Request) -> Response:
        if request.url.path == "/healthz":
            return JSONResponse(
                _health_body("disabled", 0),
                headers={
                    "traceparent": (
                        "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
                    )
                },
            )
        if request.url.path == "/readyz":
            return JSONResponse({"ready": True})
        return JSONResponse({"error": "no"}, status_code=404)

    with _wrapper(handler) as base:
        report = run_verification(base, timeout=2)
    assert _check(report, "request_id").status == "fail"
    assert "X-Request-Id" in _check(report, "request_id").detail
    assert report.ok is False


def test_unreachable_url_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    port = _closed_port()
    code = main(["--url", f"http://127.0.0.1:{port}", "--timeout", "2", "--json"])
    captured = capsys.readouterr()
    assert code == 2
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["checks"][0]["id"] == "health"
    assert payload["checks"][0]["status"] == "fail"


def test_usage_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert (
        main(
            [
                "--url",
                "http://127.0.0.1:9",
                "--token-env",
                "OMEGA_VERIFY_ABSENT",
                "--token-file",
                "ignored",
            ]
        )
        == 2
    )
    assert main(["--url", "http://127.0.0.1:9", "--timeout", "0"]) == 2
    assert (
        main(["--url", "http://127.0.0.1:9", "--token-env", "OMEGA_VERIFY_ABSENT"]) == 2
    )
    captured = capsys.readouterr()
    assert "omk_" not in captured.out + captured.err


def test_oneclick_self_test_exits_0() -> None:
    root = find_repo_root()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "omega_prime.grokbot.oneclick",
            "--self-test",
            "--root",
            str(root),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert completed.returncode == 0, (
        completed.stdout[-2000:] + completed.stderr[-2000:]
    )
    combined = completed.stdout + completed.stderr
    assert "omk_" not in combined
    assert "ok=true" in completed.stdout
    assert "shutdown=0" in completed.stdout
