"""Turnkey 1-Click Grok Bot CLI.

Orchestrates environment preflight, prompt assembly verification, manifest export,
and launches the tool host in stdio or SSE mode.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from omega_prime.grokbot.manifest import generate_manifest


def run_preflight_doctor(root: Path) -> bool:
    """Run doctor check before launching."""
    from omega_prime.grokbot.doctor import run_doctor_checks

    results = run_doctor_checks(root)
    print("\n--- Grok Bot Preflight Health Checks ---")
    for check in results.get("checks", []):
        mark = (
            "✓"
            if check["status"] == "ok"
            else ("⚠" if check["status"] == "warn" else "✗")
        )
        print(f"[{mark}] {check['name']}: {check['message']}")
        if check.get("fix_hint") and check["status"] in ("warn", "fail"):
            print(f"    → Fix hint: {check['fix_hint']}")
    print("----------------------------------------\n")
    return results.get("passed", True)


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
) -> int:
    """Execute the 1-click workflow."""
    print("=== Omega Prime ► Grok Bot Native 1-Click Launcher ===")
    print(f"Root: {root}")
    print(f"Transport: {transport}")

    if not skip_doctor:
        ok = run_preflight_doctor(root)
        if not ok:
            print(
                "WARNING: Some preflight checks failed or warned. Continuing launch..."
            )

    if export_manifest:
        host_url = f"http://{host}:{port}/sse" if transport == "sse" else ""
        manifest = generate_manifest(
            root, host_url=host_url, transport=transport, auth_token=auth_token
        )
        export_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"✓ Manifest exported to {export_manifest}")

    if dry_run:
        print("✓ Dry run requested. Exiting without launching tool host.")
        return 0

    print(f"Starting Omega Prime MCP Tool Host ({transport})...")
    if transport == "stdio":
        cmd = [
            sys.executable,
            "-m",
            "omega_prime.mcp_server",
            "--root",
            str(root),
        ]
        return subprocess.call(cmd)
    else:
        from omega_prime.grokbot.remote import serve_sse

        return serve_sse(
            root=root,
            host=host,
            port=port,
            token=auth_token or os.environ.get("MCP_AUTH_TOKEN"),
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
        "--export-manifest",
        type=Path,
        default=None,
        help="Export Grok Bot manifest JSON to file before serving",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional bearer token authentication for SSE transport",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip preflight doctor checks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run preflight and manifest export without starting server",
    )
    args = parser.parse_args(argv)

    return run_oneclick(
        args.root.resolve(),
        transport=args.transport,
        host=args.host,
        port=args.port,
        export_manifest=args.export_manifest,
        auth_token=args.token,
        skip_doctor=args.skip_doctor,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
