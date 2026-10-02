"""Phase 1: the single-seat prompt, assembler, template, and receipt check."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from omes.assemble import package_root, render, section_bullets, template_gaps, unfilled
from omes.receipts import ReceiptError, validate_receipt

ROOT = package_root()
ROSTER = ROOT / "grokbot" / "rosters" / "default.json"
ASSEMBLED = ROOT / "prompts-assembled" / "OMES.xml"
SCRIPT = ROOT / "scripts" / "assemble-prompts.sh"


def _parts(text: str) -> list[str]:
    chunks = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("<?xml") and current:
            chunks.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("".join(current))
    return chunks


def test_sources_parse():
    ET.parse(ROOT / "prompts" / "_shared" / "core-directives.xml")
    ET.parse(ROOT / "prompts" / "bot-00-omes.xml")


def test_assemble_is_deterministic_and_matches_disk():
    first = render(ROOT, ROSTER)
    second = render(ROOT, ROSTER)
    assert first == second
    assert ASSEMBLED.read_text(encoding="utf-8") == first
    assert unfilled(first) == []


def test_assemble_check_exits_zero():
    completed = subprocess.run(
        ["bash", str(SCRIPT), "--check"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "up to date" in completed.stdout


def test_assembled_prompt_points_at_skills_roster_and_prompts():
    text = ASSEMBLED.read_text(encoding="utf-8")
    parts = _parts(text)
    assert len(parts) == 2
    for part in parts:
        ET.fromstring(part)
    assert "skills" in text
    assert "contracts/tool-rosters/omes.yaml" in text
    assert "prompts/bot-00-omes.xml" in text
    assert "prompts-assembled/OMES.xml" in text
    assert "{{" not in text
    assert "bot-00-omes" in text
    assert "main" in text
    assert "2026-10-02" in text


def test_directives_require_receipt_secret_and_approval():
    text = (ROOT / "prompts" / "_shared" / "core-directives.xml").read_text(encoding="utf-8")
    root = ET.fromstring(text)
    found = {node.attrib["id"]: (node.text or "") for node in root.findall(".//directive")}
    assert "exit code" in found["PD-1"]
    assert "secret" in found["PD-4"].lower()
    assert "approval" in found["PD-5"].lower()
    assert "destructive" in found["PD-5"].lower()


def test_template_names_nothing_that_is_not_on_disk():
    template = (ROOT / "grokbot" / "templates" / "OMES.md").read_text(encoding="utf-8")
    assert section_bullets(template, "Enabled skills") == []
    assert section_bullets(template, "Routines") == []
    assert template_gaps(ROOT) == []
    assert "token" not in template.lower() or "no ids, tokens" in template.lower()


def test_template_rejects_a_skill_that_is_not_on_disk(tmp_path: Path):
    template = tmp_path / "OMES.md"
    template.write_text(
        "## Enabled skills\n\n- missing-skill\n\n## Routines\n\n- missing-routine\n",
        encoding="utf-8",
    )
    gaps = template_gaps(ROOT, template)
    assert "skills/missing-skill/SKILL.md" in gaps
    assert "routines/missing-routine.md" in gaps


def test_claim_without_a_command_fails():
    with pytest.raises(ReceiptError) as raised:
        validate_receipt(
            {
                "task_id": "phase-1",
                "bot": "bot-00-omes",
                "commands": [],
                "claims": [{"claim": "the shell is done"}],
                "unverified": [],
            }
        )
    assert any("no command" in error for error in raised.value.errors)


def test_receipt_with_a_command_passes():
    validate_receipt(
        {
            "task_id": "phase-1",
            "bot": "bot-00-omes",
            "destructive": False,
            "commands": [{"cmd": "python3 -m pytest omes/tests/test_shell.py", "exit_code": 0}],
            "claims": [{"claim": "the shell tests passed", "evidence_command_index": 0}],
            "unverified": ["live xAI call"],
        }
    )


def test_destructive_operation_without_approval_fails():
    with pytest.raises(ReceiptError) as raised:
        validate_receipt(
            {
                "task_id": "drop",
                "bot": "bot-00-omes",
                "destructive": True,
                "commands": [{"cmd": "echo drop", "exit_code": 0}],
                "claims": [{"claim": "dropped", "evidence_command_index": 0}],
                "unverified": [],
            }
        )
    assert any("without recorded approval" in error for error in raised.value.errors)


def test_self_approval_fails():
    with pytest.raises(ReceiptError) as raised:
        validate_receipt(
            {
                "task_id": "drop",
                "bot": "bot-00-omes",
                "destructive": True,
                "commands": [{"cmd": "echo drop", "exit_code": 0}],
                "claims": [{"claim": "dropped", "evidence_command_index": 0}],
                "unverified": [],
                "approvals": [{"operation": "drop", "approved_by": "bot-00-omes"}],
            }
        )
    assert any("bot itself" in error for error in raised.value.errors)
