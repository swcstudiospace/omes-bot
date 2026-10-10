"""Phase 65: captured-command receipts, operator approval, and target gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import omega_prime.receipts as receipts
from omega_prime.receipts import (
    ReceiptError,
    append_execution,
    load_executions,
    validate_receipt,
)
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.coding import register_coding_tools
from omega_prime.tools.lead import LeadClient, LeadContext
from omega_prime.tools.platform import register_platform_tools
from omega_prime.tools.quality import (
    QualityClient,
    QualityContext,
    register_quality_tools,
)
from omega_prime.tools.registry import ToolRegistry


def _isolate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OMEGA_PRIME_COMMAND_LOG", str(tmp_path / "command-log.jsonl"))
    monkeypatch.delenv("OMEGA_PRIME_STATE_DIR", raising=False)


def _cited(
    cmd: str = "pytest",
    exit_code: int = 0,
    *,
    bot: str = "bot-00-omega-prime",
    expects_failure: bool = False,
) -> dict:
    claim: dict = {"claim": "done", "evidence_command_index": 0}
    if expects_failure:
        claim["expects_failure"] = True
    return {
        "bot": bot,
        "commands": [{"cmd": cmd, "exit_code": exit_code}],
        "claims": [claim],
        "unverified": [],
    }


def test_load_executions_missing_file_is_empty(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    assert load_executions() == []


def test_command_log_is_never_inside_the_repo(tmp_path, monkeypatch):
    repo = Path(receipts.__file__).resolve().parents[1]
    inside = repo / "command-log.jsonl"
    monkeypatch.setenv("OMEGA_PRIME_COMMAND_LOG", str(inside))
    monkeypatch.setenv("OMEGA_PRIME_STATE_DIR", str(tmp_path))
    try:
        append_execution("echo", 0, "", cwd=str(tmp_path))
        assert not inside.exists()
        assert (tmp_path / "command-log.jsonl").is_file()
        assert load_executions()[0]["cmd"] == "echo"
    finally:
        inside.unlink(missing_ok=True)


def test_captured_command_verifies(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest -q", 0, "passed", cwd=str(tmp_path))
    receipt = _cited("pytest -q")
    validate_receipt(receipt, executions=load_executions())
    checked = LeadClient(LeadContext(root=tmp_path)).receipt_check(receipt)
    assert checked == {"ok": True, "bot": "bot-00-omega-prime"}


def test_forged_exit_code_fails(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest -q", 1, "failed", cwd=str(tmp_path))
    receipt = _cited("pytest -q", 0)
    with pytest.raises(ReceiptError, match="exit_code does not match"):
        validate_receipt(receipt, executions=load_executions())
    checked = LeadClient(LeadContext(root=tmp_path)).receipt_check(receipt)
    assert checked["ok"] is False


def test_uncaptured_command_fails(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest -q", 0, "", cwd=str(tmp_path))
    receipt = _cited("make deploy", 0)
    with pytest.raises(ReceiptError, match="was not captured"):
        validate_receipt(receipt, executions=load_executions())
    checked = LeadClient(LeadContext(root=tmp_path)).receipt_check(receipt)
    assert checked["ok"] is False


def test_omitted_executions_stay_structural():
    validate_receipt(_cited("never-ran", 0))


def test_expects_failure_uses_the_receipt_exit_code(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("boom", 3, "no", cwd=str(tmp_path))
    append_execution("ok", 0, "yes", cwd=str(tmp_path))
    validate_receipt(
        _cited("boom", 3, expects_failure=True), executions=load_executions()
    )
    with pytest.raises(ReceiptError, match="expects_failure"):
        validate_receipt(
            _cited("ok", 0, expects_failure=True), executions=load_executions()
        )


def test_approver_ove_stamps_bot_receipt(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest", 0, "", cwd=str(tmp_path))
    target = tmp_path / "r.json"
    target.write_text(json.dumps(_cited()), encoding="utf-8")
    client = QualityClient(QualityContext(root=tmp_path, bot_id="bot-00-omega-prime"))
    result = client.receipt_approve("r.json", approver="ove")
    assert result["ok"] is True
    assert result["approved_by"] == "ove"
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored["approved_by"] == "ove"
    assert stored["approved_at"]


def test_approver_bot_id_is_refused(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest", 0, "", cwd=str(tmp_path))
    target = tmp_path / "r.json"
    target.write_text(json.dumps(_cited()), encoding="utf-8")
    client = QualityClient(QualityContext(root=tmp_path, bot_id="bot-00-omega-prime"))
    refused = client.receipt_approve("r.json", approver="bot-00-omega-prime")
    assert "self_approval" in refused["error"]
    assert "approved_by" not in json.loads(target.read_text(encoding="utf-8"))
    other = tmp_path / "other.json"
    other.write_text(
        json.dumps(_cited(bot="bot-01-systems")),
        encoding="utf-8",
    )
    seat = client.receipt_approve("other.json", approver="bot-00-omega-prime")
    assert "self_approval" in seat["error"]


def test_registered_approver_and_gate_arguments(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    append_execution("pytest", 0, "", cwd=str(tmp_path))
    (tmp_path / "r.json").write_text(json.dumps(_cited()), encoding="utf-8")
    seen: list[tuple] = []

    def run(argv, timeout=120, cwd=None):
        seen.append((list(argv), cwd, timeout))
        return {"exit_code": 9, "stdout": "", "stderr": ""}

    approval = ApprovalLog()
    registry = ToolRegistry(approval_log=approval)
    register_quality_tools(
        registry,
        QualityClient(
            QualityContext(root=tmp_path, bot_id="bot-00-omega-prime", run=run)
        ),
    )
    schemas = {
        item["function"]["name"]: item["function"]["parameters"]
        for item in registry.schemas()
    }
    assert {"repo", "suites"} <= set(schemas["qua_gates_run"]["properties"])
    assert "repo" not in schemas["qua_gates_run"]["required"]
    assert "approver" in schemas["qua_receipt_approve"]["properties"]
    assert schemas["qua_receipt_approve"]["required"] == ["receipt_path"]
    gated = json.loads(
        registry.dispatch(
            "qua_gates_run",
            {
                "repo": str(tmp_path / "elsewhere"),
                "suites": [{"name": "custom", "argv": ["echo", "x"], "timeout": 12}],
            },
        )
    )
    assert seen == [(["echo", "x"], str(tmp_path / "elsewhere"), 12)]
    assert gated["gates"]["custom"]["exit_code"] == 9
    assert approval.approve("qua_receipt_approve", "ada").get("approved") is True
    stamped = json.loads(
        registry.dispatch(
            "qua_receipt_approve",
            {"receipt_path": "r.json", "approver": "ove"},
        )
    )
    assert stamped["approved_by"] == "ove"


def test_gates_run_pytest_in_pyproject_repo(tmp_path):
    repo = tmp_path / "app"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'app'\n", encoding="utf-8")
    seen: list[tuple] = []

    def run(argv, timeout=120, cwd=None):
        seen.append((list(argv), cwd, timeout))
        return {"exit_code": 4, "stdout": "", "stderr": "nope"}

    result = QualityClient(QualityContext(root=tmp_path / "other", run=run)).gates_run(
        repo=str(repo)
    )
    assert seen == [(["python3", "-m", "pytest", "-q"], str(repo), 600)]
    assert result["gates"]["pytest"]["exit_code"] == 4
    assert result["ok"] is False

    tests_only = tmp_path / "pkg"
    (tests_only / "tests").mkdir(parents=True)
    seen.clear()
    again = QualityClient(QualityContext(root=tests_only, run=run)).gates_run()
    assert seen == [(["python3", "-m", "pytest", "-q"], str(tests_only), 600)]
    assert again["gates"]["pytest"]["exit_code"] == 4


def test_omega_tree_selects_three_suites(tmp_path):
    repo = tmp_path / "tree"
    (repo / "omega_prime" / "tests").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'tree'\n", encoding="utf-8")
    seen: list[list[str]] = []

    def run(argv, timeout=120, cwd=None):
        seen.append(list(argv))
        key = argv[3] if len(argv) > 3 else ""
        code = {"omega_prime/tests": 0, "omega_prime/evals/cases": 2}.get(key, 5)
        return {"exit_code": code, "stdout": "", "stderr": ""}

    result = QualityClient(QualityContext(root=repo, run=run)).gates_run()
    assert seen == [
        ["python3", "-m", "pytest", "omega_prime/tests", "-q"],
        ["python3", "-m", "omega_prime.evals.runner", "omega_prime/evals/cases"],
        ["bash", "omega_prime/scripts/assemble-prompts.sh", "--check"],
    ]
    assert result["gates"]["suite"]["exit_code"] == 0
    assert result["gates"]["evals"]["exit_code"] == 2
    assert result["gates"]["assemble"]["exit_code"] == 5
    assert result["ok"] is False


def test_desk_gates_file_overrides_omega_tree(tmp_path):
    repo = tmp_path / "both"
    (repo / "omega_prime" / "tests").mkdir(parents=True)
    (repo / "omega-desk-gates.json").write_text(
        json.dumps([{"name": "lint", "argv": ["echo", "hi"], "timeout": 15}]),
        encoding="utf-8",
    )
    seen: list[tuple] = []

    def run(argv, timeout=120, cwd=None):
        seen.append((list(argv), cwd, timeout))
        return {"exit_code": 7, "stdout": "", "stderr": ""}

    result = QualityClient(QualityContext(root=repo, run=run)).gates_run()
    assert seen == [(["echo", "hi"], str(repo), 15)]
    assert result["gates"]["lint"]["exit_code"] == 7


def test_run_terminal_records_finished_commands_only(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    registry = ToolRegistry()
    register_coding_tools(registry, tmp_path)
    refused = json.loads(registry.dispatch("run_terminal", {"argv": "echo"}))
    assert "error" in refused
    assert load_executions() == []
    argv = [sys.executable, "-c", "import sys; sys.exit(2)"]
    ran = json.loads(registry.dispatch("run_terminal", {"argv": argv}))
    assert ran["exit_code"] == 2
    rows = load_executions()
    assert rows == [
        {
            "cmd": " ".join(argv),
            "exit_code": 2,
            "output_tail": rows[0]["output_tail"],
            "cwd": str(Path(tmp_path).resolve()),
        }
    ]


def test_execute_code_records_finished_commands_only(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    _isolate(monkeypatch, tmp_path)
    registry = ToolRegistry()
    register_platform_tools(registry, home=home)
    refused = json.loads(registry.dispatch("execute_code", {"code": "  "}))
    assert "error" in refused
    assert load_executions() == []
    ran = json.loads(
        registry.dispatch("execute_code", {"code": "import sys; sys.exit(4)"})
    )
    assert ran["exit_code"] == 4
    rows = load_executions()
    assert len(rows) == 1
    assert rows[0]["exit_code"] == 4
    assert rows[0]["cwd"] == str(home)
    assert "sys.exit(4)" in rows[0]["cmd"]
