"""Phase 37: setup smoke check passes and trips per check."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from omes.setup_check import main, run_checks

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent


def _mirror(root: Path) -> Path:
    """Copy the repo's omes/ tree into a fixture root."""
    dest = root / "omes"
    shutil.copytree(OMES, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def test_checks_pass_on_repo_root():
    report = run_checks(ROOT)
    assert report["passed"] is True
    assert report["roster"]["ok"] is True
    assert report["template"]["ok"] is True
    assert report["assembly"]["ok"] is True
    assert report["registry"]["ok"] is True
    assert report["ultrathink"]["ok"] is None
    assert main(["--root", str(ROOT)]) == 0


def test_each_failure_trips_its_check(tmp_path: Path, monkeypatch):
    fixture = _mirror(tmp_path / "bad")

    roster_path = fixture / "omes" / "grokbot" / "rosters" / "default.json"
    roster_path.write_text("{broken", encoding="utf-8")
    report = run_checks(fixture)
    assert report["passed"] is False
    assert report["roster"]["ok"] is False

    roster = {"bot_id": "x", "default_branch": "main", "roster_version": "1",
              "skills_dir": "skills", "prompts_dir": "prompts",
              "routines_dir": "routines", "tool_roster": "contracts/tool-rosters/omes.yaml"}
    roster_path.write_text(json.dumps(roster), encoding="utf-8")
    template = fixture / "omes" / "grokbot" / "templates" / "OMES.md"
    text = template.read_text(encoding="utf-8")
    assert text.count("## Enabled skills\n\n## Routines") == 1
    template.write_text(text.replace("## Enabled skills\n\n## Routines",
                                     "## Enabled skills\n\n- ghost-skill\n\n## Routines"),
                        encoding="utf-8")
    assert run_checks(fixture)["template"]["ok"] is False

    shutil.rmtree(fixture / "omes")
    _mirror(fixture)
    (fixture / "omes" / "prompts-assembled" / "OMES.xml").write_text("stale",
                                                                     encoding="utf-8")
    assert run_checks(fixture)["assembly"]["ok"] is False

    shutil.rmtree(fixture / "omes")
    _mirror(fixture)
    (fixture / "omes" / "contracts" / "tool-rosters" / "omes.yaml").write_text(
        "version: 1\ntools:\n", encoding="utf-8")
    assert run_checks(fixture)["registry"]["ok"] is False

    monkeypatch.setenv("ULTRATHINK_ROOT", str(tmp_path / "nowhere"))
    assert run_checks(fixture)["ultrathink"]["ok"] is False
