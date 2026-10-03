"""Phase 20: the eval runner passes shipped cases and reports failures."""

from __future__ import annotations

from pathlib import Path

from omes.evals.runner import main, run_case, run_suite

OMES = Path(__file__).resolve().parents[1]
CASES = OMES / "evals" / "cases"


def test_shipped_cases_all_pass(tmp_path: Path):
    report = run_suite(CASES, tmp_path)

    assert report["failed"] == 0
    assert report["passed"] == 6
    assert [result["id"] for result in report["results"]] == [
        "golden-greeting",
        "golden-read-roundtrip",
        "golden-no-password",
        "redteam-policy-escape",
        "redteam-exfil-blocked",
        "redteam-injection-contained",
    ]
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


def test_ci_workflow_runs_suite_evals_and_assemble():
    text = (OMES.parent / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python3 -m pytest omes/tests -q" in text
    assert "python3 -m omes.evals.runner omes/evals/cases" in text
    assert "bash omes/scripts/assemble-prompts.sh --check" in text
    assert "pull_request" in text
