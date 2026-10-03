"""Phase 33: receipts end to end over real hermetic commands.

Run local commands, cite each claim against a command + exit code,
validate the receipt, then stamp it through the quality approval tool.
Self-approval is refused at both levels. No network, no live CLIs.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from omes.receipts import ReceiptError, validate_receipt
from omes.tools.approvals import ApprovalLog
from omes.tools.quality import QualityClient, QualityContext


def _run(argv: list[str]) -> dict:
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    tail = (completed.stdout + completed.stderr)[-500:]
    return {"cmd": " ".join(argv), "exit_code": completed.returncode,
            "output_tail": tail}


def test_receipt_cites_real_commands_and_exit_codes(tmp_path):
    passing = _run([sys.executable, "-c", "print('e2e-ok')"])
    failing = _run([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert passing["exit_code"] == 0 and "e2e-ok" in passing["output_tail"]
    assert failing["exit_code"] == 3

    receipt = {
        "bot": "bot-00-omes",
        "commands": [passing, failing],
        "claims": [
            {"claim": "hermetic command ran", "evidence_command_index": 0},
            {"claim": "failing command exits 3", "evidence_command_index": 1,
             "expects_failure": True},
        ],
        "unverified": [],
    }
    validate_receipt(receipt)

    bad_claim = {"bot": "bot-00-omes", "commands": [failing],
                 "claims": [{"claim": "wrong", "evidence_command_index": 0}],
                 "unverified": []}
    with pytest.raises(ReceiptError, match="failing command"):
        validate_receipt(bad_claim)

    bypassed = {"bot": "bot-00-omes",
                "commands": [{"cmd": "deploy --no-verify", "exit_code": 0}],
                "claims": [{"claim": "deployed", "evidence_command_index": 0}],
                "unverified": []}
    with pytest.raises(ReceiptError, match="bypassed"):
        validate_receipt(bypassed)

    dangling = {"bot": "bot-00-omes", "commands": [passing],
                "claims": [{"claim": "ghost", "evidence_command_index": 5}],
                "unverified": []}
    with pytest.raises(ReceiptError, match="has no command"):
        validate_receipt(dangling)


def test_destructive_receipt_needs_another_approver_and_stamp(tmp_path):
    passing = _run([sys.executable, "-c", "print('staged')"])
    log = ApprovalLog()
    assert log.approve("infra_railway_redeploy", "ada").get("approved") is True
    assert log.approve("infra_railway_redeploy", "bot-00-omes").get("approved") is False

    receipt = {
        "bot": "bot-00-omes",
        "commands": [passing],
        "claims": [{"claim": "redeploy staged", "evidence_command_index": 0}],
        "unverified": [],
        "destructive": True,
        "approvals": [{"tool": "infra_railway_redeploy", "approved_by": "ada"}],
    }
    validate_receipt(receipt)

    selfish = dict(receipt)
    selfish["approvals"] = [{"tool": "infra_railway_redeploy",
                             "approved_by": "bot-00-omes"}]
    with pytest.raises(ReceiptError, match="itself"):
        validate_receipt(selfish)

    missing = dict(receipt)
    del missing["approvals"]
    with pytest.raises(ReceiptError, match="without recorded approval"):
        validate_receipt(missing)

    stamped_path = tmp_path / "e2e-receipt.json"
    stamped_path.write_text(json.dumps(receipt), encoding="utf-8")
    client = QualityClient(QualityContext(root=tmp_path, bot_id="bot-06-quality"))
    stamped = client.receipt_approve("e2e-receipt.json", note="e2e stamp")
    assert stamped["ok"] is True and stamped["approved_by"] == "bot-06-quality"
    assert stamped["pushed"] is False
    stored = json.loads(stamped_path.read_text(encoding="utf-8"))
    assert stored["approved_by"] == "bot-06-quality"

    selfish_path = tmp_path / "self-receipt.json"
    selfish_path.write_text(json.dumps(dict(receipt, bot="bot-06-quality")),
                            encoding="utf-8")
    refused = client.receipt_approve("self-receipt.json")
    assert "self_approval" in refused["error"]
