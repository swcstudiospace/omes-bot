"""Tests for Grok Bot Turn Emulator and Smoke Test Suite."""

import shutil
from pathlib import Path

import pytest

from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.emulator import GrokBotTurnEmulator, main
from omega_prime.grokbot.manifest import find_repo_root


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    shutil.copytree(
        find_repo_root() / "omega_prime" / "contracts",
        tmp_path / "root" / "omega_prime" / "contracts",
    )
    return tmp_path / "root"


def test_emulator_execute_existing_tool(tmp_path):
    auditor = GrokBotAuditTracer(tmp_path / "emulator_audit.jsonl")
    emulator = GrokBotTurnEmulator(auditor=auditor)

    res = emulator.execute_tool("read_file", {"path": "__init__.py"})
    assert res["status"] == "ok"
    assert "Omega Prime" in str(res["result"])

    recent = auditor.read_recent()
    assert len(recent) == 1
    assert recent[0]["tool_name"] == "read_file"


def test_emulator_execute_missing_tool(tmp_path):
    auditor = GrokBotAuditTracer(tmp_path / "emulator_audit.jsonl")
    emulator = GrokBotTurnEmulator(auditor=auditor)

    res = emulator.execute_tool("nonexistent_tool_xyz", {})
    assert "error" in res
    assert "not found" in res["error"]


def test_emulator_run_smoke_suite(tmp_path):
    auditor = GrokBotAuditTracer(tmp_path / "emulator_audit.jsonl")
    emulator = GrokBotTurnEmulator(auditor=auditor)

    results = emulator.run_smoke_suite()
    assert len(results) == 4
    for r in results:
        assert r.status == "ok", f"Scenario '{r.scenario}' failed with error: {r.error}"


def test_emulator_uses_production_runtime_and_repo_root(tmp_path):
    emulator = GrokBotTurnEmulator(
        auditor=GrokBotAuditTracer(tmp_path / "audit.jsonl"),
        home=tmp_path / "home",
        env={},
    )
    assert emulator.root == find_repo_root()
    assert emulator.runtime.roster
    assert emulator.runtime.tool_names
    assert emulator.registry is emulator.runtime.registry


def test_emulator_denies_tool_outside_roster(repo_copy, tmp_path):
    roster = (
        repo_copy / "omega_prime" / "contracts" / "tool-rosters" / "omega-prime.yaml"
    )
    roster.write_text("tools:\n  - todo_read\n", encoding="utf-8")
    auditor = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    emulator = GrokBotTurnEmulator(repo_copy, auditor, home=tmp_path / "home", env={})

    assert emulator.runtime.tool_names == ["todo_read"]
    denied = emulator.execute_tool("read_file", {"path": "__init__.py"})
    assert denied["status"] == "error"
    assert "not found" in denied["error"]
    assert "result" not in denied
    assert emulator.execute_tool("todo_read", {})["status"] == "ok"

    records = auditor.read_recent()
    assert [(r["tool_name"], r["status"]) for r in records] == [
        ("read_file", "denied"),
        ("todo_read", "ok"),
    ]
    assert {r["caller"] for r in records} == {"emulator"}


def test_emulator_approval_scenario(tmp_path):
    auditor = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    emulator = GrokBotTurnEmulator(auditor=auditor, home=tmp_path / "home", env={})

    results = emulator.run_approval_scenario()
    assert len(results) == 2
    refused, passed = results
    assert refused.tool_name == passed.tool_name
    assert refused.tool_name in emulator.runtime.gated_tools
    for r in results:
        assert r.status == "ok", f"Scenario '{r.scenario}' failed with error: {r.error}"
    # The probe sends no arguments: the registry rejects it before the tool body.
    assert "missing required arguments" in str(passed.result)
    assert not emulator.runtime.approval_log.is_approved(refused.tool_name)


def test_emulator_constructor_approval_opens_the_gate(tmp_path):
    base = GrokBotTurnEmulator(
        auditor=GrokBotAuditTracer(tmp_path / "audit.jsonl"),
        home=tmp_path / "home",
        env={},
    )
    tool = base._approval_probe()
    assert tool is not None

    refused = base.execute_tool(tool, {})
    assert refused["status"] == "error"
    assert "approval required" in refused["error"]

    approved = GrokBotTurnEmulator(
        auditor=GrokBotAuditTracer(tmp_path / "audit2.jsonl"),
        home=tmp_path / "home",
        approvals=[(tool, "alice")],
        env={},
    )
    passed = approved.execute_tool(tool, {})
    assert passed["status"] == "error"
    assert "approval required" not in passed["error"]
    assert "missing required arguments" in passed["error"]


def test_emulator_audit_records_caller_and_chain_verifies(tmp_path):
    auditor = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    emulator = GrokBotTurnEmulator(auditor=auditor, home=tmp_path / "home", env={})

    emulator.execute_tool("todo_read", {})
    emulator.execute_tool("clarify", {"question": "What is the next phase?"})
    emulator.execute_tool("nonexistent_tool_xyz", {})
    emulator.run_approval_scenario()

    records = auditor.read_recent()
    assert len(records) == 3 + 2
    assert {r["caller"] for r in records} == {"emulator"}
    assert {r["event"] for r in records} == {"tool_call"}
    ok, count, message = auditor.verify_integrity()
    assert ok, message
    assert count == len(records)


def test_main_smoke_exits_1_when_a_scenario_fails(repo_copy, capsys):
    # The copy has no omega_prime/__init__.py, so the first scenario fails.
    with pytest.raises(SystemExit) as exc:
        main(["--smoke", "--root", str(repo_copy)])
    assert exc.value.code == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_rejects_malformed_approval(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--smoke", "--approve", "no-approver"])
    assert exc.value.code == 2
    assert "TOOL:APPROVER" in capsys.readouterr().err
