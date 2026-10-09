# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Turnkey 1-Click Grok Bot CLI.

Orchestrates environment preflight, bind-safety evaluation, manifest export, and
launches the tool host in stdio or SSE mode.

Exit codes: 0 success, 2 configuration error (bad token, unsafe bind, ...), 3 strict
preflight failure. Secrets come from a 0600 token file, a hashed token store, the
environment, or (deprecated) argv; a token is never written to the manifest, printed
to stdout, or put in JSON output.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlsplit

from omega_prime.grokbot import doctor as _doctor
from omega_prime.grokbot._io import atomic_write_text, read_secret_file
from omega_prime.grokbot.manifest import generate_manifest
from omega_prime.grokbot.security import (
    SecurityConfigError,
    TokenStore,
    check_bind_safety,
    generate_token,
)

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_PREFLIGHT = 3

DEFAULT_TOKEN_ENV = "MCP_AUTH_TOKEN"
_WILDCARD_HOSTS = frozenset({"", "0.0.0.0", "::", "[::]"})
_PREFIX = "omega-prime-oneclick"


def run_doctor_checks(
    root: Path, port: int, *, host: str, auth_enabled: bool
) -> dict[str, Any]:
    """The doctor entry point used by the launcher (looked up at call time)."""
    return _doctor.run_doctor_checks(root, port, host=host, auth_enabled=auth_enabled)


def _err(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _fail(message: str) -> int:
    _err(f"{_PREFIX}: {message}")
    return EXIT_CONFIG


def _run_preflight(
    root: Path,
    port: int,
    host: str,
    auth_enabled: bool,
    stream: TextIO,
) -> dict[str, Any]:
    """Run the doctor and print every check to `stream`."""
    results = run_doctor_checks(root, port, host=host, auth_enabled=auth_enabled)
    print("\n--- Grok Bot Preflight Health Checks ---", file=stream)
    for check in results.get("checks", []):
        mark = (
            "✓"
            if check["status"] == "ok"
            else ("⚠" if check["status"] == "warn" else "✗")
        )
        print(f"[{mark}] {check['name']}: {check['message']}", file=stream)
        if check.get("fix_hint") and check["status"] in ("warn", "fail"):
            print(f"    → Fix hint: {check['fix_hint']}", file=stream)
    print("----------------------------------------\n", file=stream)
    return results


def run_preflight_doctor(
    root: Path,
    *,
    port: int = 8000,
    host: str = "127.0.0.1",
    auth_enabled: bool = False,
) -> bool:
    """Run doctor checks, print them, and return whether none failed."""
    results = _run_preflight(root, port, host, auth_enabled, sys.stdout)
    return bool(results.get("passed", True))


def _url_host(host: str) -> str:
    """Host usable in a client URL: wildcard binds become loopback."""
    name = host.strip()
    if name in _WILDCARD_HOSTS:
        return "127.0.0.1"
    if ":" in name and not name.startswith("["):
        return f"[{name}]"
    return name


def _sse_url(host: str, port: int, public_url: str | None) -> str:
    if public_url:
        return public_url.rstrip("/") + "/sse"
    return f"http://{_url_host(host)}:{port}/sse"


def _resolve_token(
    token_file: Path | None,
    argv_token: str | None,
    token_env: str,
    *,
    will_generate: bool,
) -> tuple[str | None, str]:
    """Token and its source ("file", "argv", "env", "none"), file > argv > env.

    A `--token-file` that does not exist yet is only acceptable when a token will be
    generated into it. Raises `ValueError`/`SecurityConfigError` on bad configuration.
    """
    token: str | None = None
    source = "none"
    if token_file is not None and (token_file.exists() or not will_generate):
        token, source = read_secret_file(token_file), "file"
    elif argv_token:
        token, source = argv_token, "argv"
    else:
        value = os.environ.get(token_env, "").strip()
        if value:
            token, source = value, "env"
    if token is not None:
        TokenStore.from_token(token)  # enforces the minimum length
    return token, source


@contextlib.contextmanager
def _exported_token(name: str, token: str | None) -> Iterator[None]:
    """Expose `token` as env var `name` for this process only."""
    if token is None:
        yield
        return
    previous = os.environ.get(name)
    os.environ[name] = token
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _announce_generated_token(token: str, token_file: Path | None) -> None:
    _err(f"Generated bearer token (shown only once): {token}")
    _err(
        "Put it in the Grok Bot connector settings; store it with "
        "--token-file PATH to reuse it."
    )
    if token_file is not None:
        atomic_write_text(token_file, token + "\n")
        _err(f"Token also written to {token_file} (mode 0600).")


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def run_oneclick(
    root: Path,
    *,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    export_manifest: Path | None = None,
    auth_token: str | None = None,
    skip_doctor: bool = False,
    dry_run: bool = False,
    public_url: str | None = None,
    token_env: str = DEFAULT_TOKEN_ENV,
    token_file: Path | None = None,
    generate_new_token: bool = False,
    allowed_hosts: Sequence[str] = (),
    allowed_origins: Sequence[str] = (),
    audit_log: Path | None = None,
    allow_insecure_no_auth: bool = False,
    strict: bool | None = None,
    json_output: bool = False,
    token_store_path: Path | None = None,
    log_format: str = "text",
) -> int:
    """Execute the 1-click workflow."""
    sse = transport == "sse"
    strict = sse if strict is None else strict
    say = sys.stderr if json_output else sys.stdout

    print("=== Omega Prime ► Grok Bot Native 1-Click Launcher ===", file=say)
    print(f"Root: {root}", file=say)
    print(f"Transport: {transport}", file=say)

    if generate_new_token and not sse:
        return _fail("--generate-token requires --transport sse")
    if public_url:
        parts = urlsplit(public_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            return _fail("--public-url must be an http(s) URL")

    # --- Secrets and bind safety: nothing is written or served before this passes.
    token: str | None = None
    token_source = "none"
    generated = False
    if sse:
        try:
            token, token_source = _resolve_token(
                token_file, auth_token, token_env, will_generate=generate_new_token
            )
        except ValueError as exc:  # includes SecurityConfigError
            return _fail(str(exc))
        if generate_new_token:
            if token is None:
                token, token_source, generated = generate_token(), "generated", True
            else:
                _err(
                    f"{_PREFIX}: a token is already configured; "
                    "--generate-token ignored"
                )
    if sse and token is None and token_store_path is not None:
        token_source = "store"
    auth_enabled = token is not None or token_source == "store"
    if sse:
        try:
            check_bind_safety(
                host, auth_enabled=auth_enabled, allow_insecure=allow_insecure_no_auth
            )
        except SecurityConfigError as exc:
            return _fail(str(exc))
        if allow_insecure_no_auth and not auth_enabled:
            _err(
                f"{_PREFIX}: WARNING: serving without authentication "
                "(--allow-insecure-no-auth)"
            )

    # --- Preflight.
    checks: list[dict[str, Any]] = []
    passed: bool | None = None
    url = _sse_url(host, port, public_url) if sse else None
    auth_info = {
        "enabled": auth_enabled,
        "type": "bearer" if auth_enabled else "none",
        "token_env": token_env,
        "source": token_source,
    }

    def report(manifest_path: Path | None) -> dict[str, Any]:
        return {
            "passed": passed,
            "strict": strict,
            "checks": checks,
            "transport": transport,
            "url": url,
            "manifest_path": str(manifest_path) if manifest_path else None,
            "auth": auth_info,
        }

    if not skip_doctor:
        results = _run_preflight(root, port, host, auth_enabled, say)
        checks = list(results.get("checks", []))
        failures = [c for c in checks if c.get("status") == "fail"]
        passed = bool(results.get("passed", not failures)) and not failures
        if not passed:
            if strict:
                print(
                    f"ERROR: {len(failures)} preflight check(s) failed; aborting "
                    "(strict). Fix them or pass --no-strict to continue anyway.",
                    file=sys.stderr,
                    flush=True,
                )
                if json_output:
                    _emit_json(report(None))
                return EXIT_PREFLIGHT
            print(
                "WARNING: Some preflight checks failed. Continuing launch...",
                file=say,
            )

    # --- Manifest (never contains the token).
    manifest_path: Path | None = None
    if export_manifest or dry_run:
        try:
            manifest = generate_manifest(
                root,
                host_url=url or "",
                transport=transport,
                public_url=public_url if sse else None,
                auth_enabled=auth_enabled,
                token_env=token_env,
            )
        except ValueError as exc:
            return _fail(str(exc))
        if export_manifest:
            atomic_write_text(
                export_manifest, json.dumps(manifest, indent=2) + "\n", mode=0o644
            )
            manifest_path = export_manifest
            print(f"✓ Manifest exported to {export_manifest}", file=say)

    if dry_run:
        print("✓ Dry run requested. Exiting without launching tool host.", file=say)
        if json_output:
            _emit_json(report(manifest_path))
        return EXIT_OK

    if json_output:
        _emit_json(report(manifest_path))

    if generated and token is not None:
        _announce_generated_token(token, token_file)

    print(f"Starting Omega Prime MCP Tool Host ({transport})...", file=say, flush=True)
    if not sse:
        cmd = [sys.executable, "-m", "omega_prime.mcp_server", "--root", str(root)]
        if audit_log is not None:
            cmd += ["--audit-log", str(audit_log)]
        return subprocess.call(cmd)

    from omega_prime.grokbot.remote import serve_sse

    audit = None
    if audit_log is not None:
        from omega_prime.grokbot.audit import GrokBotAuditTracer

        audit = GrokBotAuditTracer(audit_log)
    with _exported_token(token_env, token):
        return serve_sse(
            root=root,
            host=host,
            port=port,
            token=token,
            public_url=public_url,
            allowed_hosts=tuple(allowed_hosts),
            allowed_origins=tuple(allowed_origins),
            allow_insecure_no_auth=allow_insecure_no_auth,
            audit=audit,
            token_store_path=token_store_path,
            log_format=log_format,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omega-prime-grokbot-oneclick")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type for MCP (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE server")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server")
    parser.add_argument(
        "--public-url",
        default=None,
        help="Externally reachable base URL (exported as <url>/sse in the manifest)",
    )
    parser.add_argument(
        "--export-manifest",
        type=Path,
        default=None,
        help="Export Grok Bot manifest JSON to file before serving",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Env var holding the bearer token (default: {DEFAULT_TOKEN_ENV})",
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=None,
        help="File (mode 0600) holding the bearer token",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="DEPRECATED: bearer token on the command line (visible to other users); "
        "use --token-file or --token-env",
    )
    parser.add_argument(
        "--generate-token",
        action="store_true",
        help="SSE only: mint a bearer token when none is configured and show it once",
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        help="Allowed browser Origin for SSE (repeatable)",
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Allowed Host header value for SSE (repeatable)",
    )
    parser.add_argument(
        "--audit-log", type=Path, default=None, help="Audit log path for tool calls"
    )
    parser.add_argument(
        "--allow-insecure-no-auth",
        action="store_true",
        help="Permit an unauthenticated listener on a non-loopback address",
    )
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Abort when a preflight check fails (default: on for sse, off for stdio)",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip preflight doctor checks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run preflight, bind safety and manifest export without starting server",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one machine-readable JSON object on stdout (text goes to stderr)",
    )
    parser.add_argument(
        "--token-store",
        type=Path,
        default=None,
        metavar="PATH",
        help="hashed token store; counts as authentication for bind safety",
    )
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="log format forwarded to the SSE host (default: text)",
    )
    args = parser.parse_args(argv)

    if args.token:
        _err(
            f"{_PREFIX}: WARNING: --token is visible to other users in the process "
            "list; prefer --token-file or the environment variable."
        )

    return run_oneclick(
        args.root.resolve(),
        transport=args.transport,
        host=args.host,
        port=args.port,
        export_manifest=args.export_manifest,
        auth_token=args.token,
        skip_doctor=args.skip_doctor,
        dry_run=args.dry_run,
        public_url=args.public_url,
        token_env=args.token_env,
        token_file=args.token_file,
        generate_new_token=args.generate_token,
        allowed_hosts=args.allow_host,
        allowed_origins=args.allow_origin,
        audit_log=args.audit_log,
        allow_insecure_no_auth=args.allow_insecure_no_auth,
        strict=args.strict,
        json_output=args.json,
        token_store_path=args.token_store,
        log_format=args.log_format,
    )


if __name__ == "__main__":
    sys.exit(main())
