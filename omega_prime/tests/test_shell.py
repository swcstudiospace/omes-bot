"""Phase 1: the single-seat prompt, assembler, template, and receipt check."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from omega_prime.assemble import (
    assembled_path,
    main,
    package_root,
    render,
    template_gaps,
    unfilled,
)
from omega_prime.receipts import ReceiptError, validate_receipt
from omega_prime.tools.agent_message import MESSAGING_TOOL_NAMES
from omega_prime.tools.autonomous import AUTONOMOUS_TOOL_NAMES
from omega_prime.tools.goals import GOAL_TOOL_NAMES
from omega_prime.tools.harness import HARNESS_TOOL_NAMES
from omega_prime.tools.heartbeat import HEARTBEAT_TOOL_NAMES
from omega_prime.tools.prime_runtime import KERNEL_TOOL_NAMES
from omega_prime.tools.rlm import RLM_TOOL_NAMES

ROOT = package_root()
ROSTER = ROOT / "grokbot" / "rosters" / "default.json"


def test_template_rejects_a_skill_that_is_not_on_disk(tmp_path: Path):
    template = tmp_path / "OMEGA_PRIME.md"
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
                "bot": "bot-00-omega-prime",
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
            "bot": "bot-00-omega-prime",
            "destructive": False,
            "commands": [
                {
                    "cmd": "python3 -m pytest omega_prime/tests/test_shell.py",
                    "exit_code": 0,
                }
            ],
            "claims": [
                {"claim": "the shell tests passed", "evidence_command_index": 0}
            ],
            "unverified": ["live xAI call"],
        }
    )


def test_destructive_operation_without_approval_fails():
    with pytest.raises(ReceiptError) as raised:
        validate_receipt(
            {
                "task_id": "drop",
                "bot": "bot-00-omega-prime",
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
                "bot": "bot-00-omega-prime",
                "destructive": True,
                "commands": [{"cmd": "echo drop", "exit_code": 0}],
                "claims": [{"claim": "dropped", "evidence_command_index": 0}],
                "unverified": [],
                "approvals": [
                    {"operation": "drop", "approved_by": "bot-00-omega-prime"}
                ],
            }
        )
    assert any("bot itself" in error for error in raised.value.errors)


_PRIME_FAMILY_NAMES = {
    "rlm": tuple(RLM_TOOL_NAMES),
    "harness": tuple(HARNESS_TOOL_NAMES),
    "goals": tuple(GOAL_TOOL_NAMES),
    "heartbeat": tuple(HEARTBEAT_TOOL_NAMES),
    "autonomous": tuple(AUTONOMOUS_TOOL_NAMES),
    "messaging": tuple(MESSAGING_TOOL_NAMES),
    "kernel": tuple(KERNEL_TOOL_NAMES),
}

_ALL_PRIME_NAMES = [name for names in _PRIME_FAMILY_NAMES.values() for name in names]


def _offered(text: str, name: str) -> bool:
    return f'<tool name="{name}"/>' in text


def test_default_render_omits_every_disabled_prime_family():
    text = render(ROOT, ROSTER)
    assert unfilled(text) == []
    for name in _ALL_PRIME_NAMES:
        assert not _offered(text, name), f"disabled family tool offered: {name}"
    for name in (
        "read_file",
        "run_terminal",
        "delegate_task",
        "lead_brief",
        "sys_index_query",
        "web_vercel_deployments",
        "ult_status",
        "substrate_docs_search",
    ):
        assert _offered(text, name), f"ordinary tool missing: {name}"


def test_enabled_family_appears_without_leaking_other_families():
    text = render(ROOT, ROSTER, {"prime": {"rlm": {"enabled": True}}})
    assert unfilled(text) == []
    for name in _PRIME_FAMILY_NAMES["rlm"]:
        assert _offered(text, name), f"enabled family tool missing: {name}"
    for family, names in _PRIME_FAMILY_NAMES.items():
        if family == "rlm":
            continue
        for name in names:
            assert not _offered(text, name), f"disabled family {family} leaked: {name}"
    assert _offered(text, "read_file")
    assert _offered(text, "delegate_task")


def test_default_render_ignores_process_environment_flags(monkeypatch):
    monkeypatch.setenv("OMEGA_PRIME_PRIME_RLM_ENABLED", "1")
    monkeypatch.setenv("OMEGA_PRIME_PRIME_KERNEL_ENABLED", "true")
    text = render(ROOT, ROSTER)
    for name in _ALL_PRIME_NAMES:
        assert not _offered(text, name), f"disabled family tool offered: {name}"


def test_explicit_config_enables_only_its_family(monkeypatch):
    from omega_prime.config import load_config

    for family in _PRIME_FAMILY_NAMES:
        monkeypatch.delenv(f"OMEGA_PRIME_PRIME_{family.upper()}_ENABLED", raising=False)

    monkeypatch.setenv("OMEGA_PRIME_PRIME_HARNESS_ENABLED", "true")
    text = render(ROOT, ROSTER, load_config())
    for name in _PRIME_FAMILY_NAMES["harness"]:
        assert _offered(text, name), f"enabled family tool missing: {name}"
    for family, names in _PRIME_FAMILY_NAMES.items():
        if family == "harness":
            continue
        for name in names:
            assert not _offered(text, name), f"disabled family {family} leaked: {name}"


def _scratch_root(tmp_path: Path) -> Path:
    """A private copy of the assembler inputs, with a canonical artifact."""
    root = tmp_path / "root"
    for name in ("prompts", "grokbot", "skills", "routines"):
        shutil.copytree(ROOT / name, root / name)
    assert main(["--root", str(root)]) == 0
    return root


def test_enabled_family_output_leaves_the_canonical_artifact_untouched(tmp_path: Path):
    root = _scratch_root(tmp_path)
    canonical = assembled_path(root)
    before = canonical.read_bytes()
    output = tmp_path / "experiment" / "enabled.xml"

    args = ["--root", str(root), "--enable-family", "rlm", "--output", str(output)]

    assert main(args) == 0

    text = output.read_text(encoding="utf-8")
    for name in _PRIME_FAMILY_NAMES["rlm"]:
        assert _offered(text, name), f"enabled family tool missing: {name}"
    for family, names in _PRIME_FAMILY_NAMES.items():
        if family == "rlm":
            continue
        for name in names:
            assert not _offered(text, name), f"disabled family {family} leaked: {name}"
    assert canonical.read_bytes() == before


def test_enable_family_without_output_is_refused_and_writes_nothing(tmp_path: Path):
    root = _scratch_root(tmp_path)
    canonical = assembled_path(root)
    before = canonical.read_bytes()
    entries = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    with pytest.raises(SystemExit) as raised:
        main(["--root", str(root), "--enable-family", "rlm"])
    assert raised.value.code == 2
    with pytest.raises(SystemExit) as raised:
        main(["--root", str(root), "--enable-family", "rlm", "--check"])
    assert raised.value.code == 2

    assert canonical.read_bytes() == before
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == entries


def test_default_output_redirects_write_and_check_away_from_canonical(tmp_path: Path):
    root = _scratch_root(tmp_path)
    canonical = assembled_path(root)
    before = canonical.read_bytes()
    output = tmp_path / "copy.xml"

    assert main(["--root", str(root), "--output", str(output)]) == 0
    assert output.read_bytes() == before

    output.write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        main(["--root", str(root), "--check", "--output", str(output)])
    assert isinstance(raised.value.code, str)
    assert canonical.read_bytes() == before


def test_enabled_family_check_compares_the_output_path(tmp_path: Path):
    root = _scratch_root(tmp_path)
    canonical = assembled_path(root)
    before = canonical.read_bytes()
    output = tmp_path / "enabled.xml"
    enabled = ["--root", str(root), "--enable-family", "rlm", "--output", str(output)]

    with pytest.raises(SystemExit) as raised:
        main([*enabled, "--check"])
    assert isinstance(raised.value.code, str)
    assert not output.exists()

    assert main(enabled) == 0
    written = output.read_bytes()
    assert main([*enabled, "--check"]) == 0

    output.write_text("drifted\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        main([*enabled, "--check"])
    assert isinstance(raised.value.code, str)
    assert output.read_text(encoding="utf-8") == "drifted\n"
    assert written != output.read_bytes()
    assert canonical.read_bytes() == before
