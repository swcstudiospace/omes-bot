"""Tests for Grok Bot 1-Click Launcher."""

import json
from pathlib import Path

from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.oneclick import run_oneclick


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
        auth_token="test-secret",
        export_manifest=manifest_out,
        dry_run=True,
    )
    assert ret == 0
    assert manifest_out.is_file()

    data = json.loads(manifest_out.read_text(encoding="utf-8"))
    assert data["mcp_server"]["transport"] == "sse"
    assert data["mcp_server"]["url"] == "http://127.0.0.1:59125/sse"
    assert data["mcp_server"]["auth"]["type"] == "bearer"
