"""Tests for Grok Bot Turn Emulator and Smoke Test Suite."""

from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.grokbot.emulator import GrokBotTurnEmulator


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
