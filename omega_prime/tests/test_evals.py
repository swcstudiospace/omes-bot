"""Phase 20: the eval runner passes shipped cases and reports failures."""

from __future__ import annotations

import json
from pathlib import Path

import omega_prime.tools.ultrathink as ultrathink_tools
from omega_prime.evals.runner import main, run_case, run_suite

OMEGA_PRIME = Path(__file__).resolve().parents[1]
CASES = OMEGA_PRIME / "evals" / "cases"


def _load_cases(name: str) -> list[dict]:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


def _mark_cases() -> tuple[dict, dict]:
    golden = next(
        case
        for case in _load_cases("golden.json")
        if case["id"] == "golden-ultrathink-mark-approved"
    )
    redteam = next(
        case
        for case in _load_cases("redteam.json")
        if case["id"] == "redteam-ultrathink-mark-unapproved"
    )
    return golden, redteam


def test_shipped_cases_all_pass(tmp_path: Path):
    report = run_suite(CASES, tmp_path)

    assert report["failed"] == 0
    assert main([str(CASES)]) == 0


def test_failing_and_malformed_cases_report_without_raising(tmp_path: Path):
    bad = run_case(
        {
            "id": "bad-golden",
            "user": "hi",
            "script": [{"role": "assistant", "content": "hello"}],
            "expect": [{"type": "final_contains", "text": "goodbye"}],
        },
        tmp_path,
    )
    assert bad["passed"] is False
    assert any("goodbye" in failure for failure in bad["failures"])

    unknown = run_case(
        {
            "id": "bad-type",
            "user": "hi",
            "script": [{"role": "assistant", "content": "hello"}],
            "expect": [{"type": "vibes", "level": 11}],
        },
        tmp_path,
    )
    assert unknown["passed"] is False
    assert any("unknown expectation type" in failure for failure in unknown["failures"])


def test_mark_approval_removal_breaks_redteam_eval(tmp_path: Path, monkeypatch):
    """Sensitivity: dropping mark approval must break the unapproved eval."""
    golden, redteam = _mark_cases()
    scrubbed = frozenset(
        name for name in ultrathink_tools.APPROVAL_TOOLS if name != "ult_session_mark"
    )
    monkeypatch.setattr(ultrathink_tools, "APPROVAL_TOOLS", scrubbed)

    try:
        broken = run_case(dict(redteam), tmp_path / "sensitivity-red")
        assert broken["passed"] is False
        assert any(
            "approval required" in failure or "was called" in failure
            for failure in broken["failures"]
        )
    finally:
        monkeypatch.undo()
    assert run_case(dict(redteam), tmp_path / "sensitivity-restored")["passed"] is True
    assert run_case(dict(golden), tmp_path / "sensitivity-golden")["passed"] is True
