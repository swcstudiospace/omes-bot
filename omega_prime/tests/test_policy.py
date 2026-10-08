"""Phase 13: seat policy, enforcement, advisor, and audit log."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omega_prime.audit.log import AuditLog
from omega_prime.policy.advisor import diff_policy
from omega_prime.policy.policy import SeatPolicy
from omega_prime.tools.coding import register_coding_tools
from omega_prime.tools.registry import ToolRegistry

OMEGA_PRIME = Path(__file__).resolve().parents[1]
POLICY = OMEGA_PRIME / "contracts" / "policies" / "omega-prime.json"
ROSTER = OMEGA_PRIME / "contracts" / "tool-rosters" / "omega-prime.yaml"


def _roster_names(text: str) -> list[str]:
    names: list[str] = []
    in_tools = False
    for line in text.splitlines():
        if line.startswith("tools:"):
            in_tools = True
            continue
        if not in_tools:
            continue
        if line.startswith("  - "):
            names.append(line[4:].strip())
            continue
        if line.strip() and not line.startswith("#") and not line.startswith(" "):
            break
    return names


def _load(payload: str) -> dict:
    return json.loads(payload)


def test_shipped_policy_governs_tools_paths_and_hosts():
    policy = SeatPolicy.load(POLICY)

    assert policy.seat == "bot-00-omega-prime"
    for name in _roster_names(ROSTER.read_text(encoding="utf-8")):
        assert policy.allows_tool(name)
    assert not policy.allows_tool("made_up_tool")

    assert not policy.allows_write("prompts/bot-00-omega-prime.xml")
    assert not policy.allows_write("contracts/tool-rosters/omega-prime.yaml")
    assert not policy.allows_write("ownership.yaml")
    assert policy.allows_write("src/code.py")

    assert not policy.allows_host("api.x.ai")
    assert not policy.allows_host("")


def test_registry_refuses_a_disallowed_tool_before_execution(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "note.txt").write_text("hi", encoding="utf-8")
    policy = SeatPolicy(
        {"version": 1, "tools": {"allow": ["read_file"]}, "paths": {}, "network": {}}
    )
    registry = ToolRegistry(policy=policy)
    register_coding_tools(registry, root)

    refused = _load(registry.dispatch("write_file", {"path": "x", "content": "y"}))
    assert refused == {"error": "policy forbids write_file", "tool": "write_file"}
    assert not (root / "x").exists()

    read = _load(registry.dispatch("read_file", {"path": "note.txt"}))
    assert read["content"] == "hi"

    open_registry = ToolRegistry()
    register_coding_tools(open_registry, root)
    wrote = _load(
        open_registry.dispatch("write_file", {"path": "ok.txt", "content": "z"})
    )
    assert "error" not in wrote


def test_writes_to_read_only_paths_leave_files_unchanged(tmp_path: Path):
    root = tmp_path / "ws"
    (root / "prompts").mkdir(parents=True)
    target = root / "prompts" / "seat.xml"
    target.write_bytes(b"<seat/>\n")
    before = target.read_bytes()
    policy = SeatPolicy.load(POLICY)
    registry = ToolRegistry(policy=policy)
    register_coding_tools(registry, root, policy=policy)

    refused = _load(
        registry.dispatch("write_file", {"path": "prompts/new.md", "content": "x"})
    )
    assert refused["error"] == "policy forbids writing prompts/new.md"
    assert not (root / "prompts" / "new.md").exists()

    diff = "@@ -1 +1 @@\n-<seat/>\n+<seat changed/>\n"
    for tool in ("patch_file", "edit_file"):
        outcome = _load(
            registry.dispatch(tool, {"path": "prompts/seat.xml", "diff": diff})
        )
        assert outcome["error"] == "policy forbids writing prompts/seat.xml"
    assert target.read_bytes() == before

    allowed = _load(
        registry.dispatch("write_file", {"path": "src/a.py", "content": "1"})
    )
    assert "error" not in allowed


def test_advisor_flags_expansions_and_ignores_narrowing():
    old = {
        "version": 1,
        "tools": {"allow": ["read_file"]},
        "paths": {"read_only": ["prompts/**", "contracts/**"]},
        "network": {"hosts": []},
    }
    new = {
        "version": 1,
        "tools": {"allow": ["read_file", "write_file"]},
        "paths": {"read_only": ["prompts/**"]},
        "network": {"hosts": ["api.x.ai"]},
    }
    report = diff_policy(old, new)

    assert report["added_tools"] == ["write_file"]
    assert report["added_hosts"] == ["api.x.ai"]
    assert report["readonly_removed"] == ["contracts/**"]
    assert report["expansions"] == [
        "tool newly allowed: write_file",
        "host newly allowed: api.x.ai",
        "read-only protection removed: contracts/**",
    ]

    narrowed = diff_policy(
        {"version": 1}, {"version": 1, "tools": {"allow": ["read_file"]}}
    )
    assert narrowed["expansions"] == []
    widened = diff_policy(
        {"version": 1, "tools": {"allow": ["read_file"]}}, {"version": 1}
    )
    assert widened["expansions"] == ["tools widened to allow-all"]


def test_audit_log_records_every_dispatch(tmp_path: Path):
    log = AuditLog(tmp_path / "audit.ndjson")
    registry = ToolRegistry(audit=log)
    registry.register(
        "ok", "d", {"type": "object", "properties": {}}, lambda: {"fine": True}
    )

    def boom():
        raise RuntimeError("kaput")

    registry.register("bad", "d", {"type": "object", "properties": {}}, boom)

    registry.dispatch("ok", {})
    registry.dispatch("nope", {})
    registry.dispatch("bad", {})

    records = AuditLog(tmp_path / "audit.ndjson").records()
    assert [record["seq"] for record in records] == [1, 2, 3]
    assert [(record["tool"], record["verdict"]) for record in records] == [
        ("ok", "allowed"),
        ("nope", "unknown"),
        ("bad", "error"),
    ]
    assert all(record["ts"].endswith("Z") for record in records)
    assert all("arguments" not in record for record in records)

    denied_log = AuditLog(tmp_path / "denied.ndjson")
    denied_registry = ToolRegistry(
        policy=SeatPolicy({"version": 1, "tools": {"allow": []}}),
        audit=denied_log,
    )
    denied_registry.register(
        "ok", "d", {"type": "object", "properties": {}}, lambda: True
    )
    denied_registry.dispatch("ok", {})
    assert [record["verdict"] for record in denied_log.violations()] == ["denied"]


def test_corrupt_audit_line_and_malformed_policy_raise(tmp_path: Path):
    audit_path = tmp_path / "audit.ndjson"
    audit_path.write_text('{"seq": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        AuditLog(audit_path).records()

    bad_policy = tmp_path / "policy.json"
    bad_policy.write_text('{"version": 2}', encoding="utf-8")
    with pytest.raises(ValueError):
        SeatPolicy.load(bad_policy)
    with pytest.raises(FileNotFoundError):
        SeatPolicy.load(tmp_path / "missing.json")
