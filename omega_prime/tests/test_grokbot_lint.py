"""Tests for the Grok Bot template lint (skills and routines resolve to files)."""

from pathlib import Path

from omega_prime.grokbot.manifest import TemplateLint, find_repo_root, lint_template

TEMPLATE = """# Test

## Name

Test

## Enabled skills

- alpha
- beta
- ../escape

## Routines

- one — does the first thing — with a second dash
- two
- three — also missing
"""


def _tree(base: Path, *, template: str = TEMPLATE) -> Path:
    pkg = base / "omega_prime"
    (pkg / "grokbot" / "templates").mkdir(parents=True)
    (pkg / "grokbot" / "templates" / "OMEGA_PRIME.md").write_text(
        template, encoding="utf-8"
    )
    (pkg / "skills" / "alpha").mkdir(parents=True)
    (pkg / "skills" / "alpha" / "SKILL.md").write_text("# alpha\n", encoding="utf-8")
    (pkg / "routines").mkdir()
    (pkg / "routines" / "one.md").write_text("# one\n", encoding="utf-8")
    return base


def test_missing_skills_and_routines_are_listed(tmp_path: Path):
    lint = lint_template(_tree(tmp_path))
    assert lint == TemplateLint(
        missing_skills=["beta", "../escape"], missing_routines=["two", "three"]
    )
    assert lint.ok is False


def test_routine_name_is_the_text_before_the_first_em_dash(tmp_path: Path):
    lint = lint_template(_tree(tmp_path))
    assert "one" not in lint.missing_routines
    assert not any("—" in name for name in lint.missing_routines)


def test_directory_without_skill_file_is_missing(tmp_path: Path):
    root = _tree(tmp_path)
    (root / "omega_prime" / "skills" / "beta").mkdir()
    assert "beta" in lint_template(root).missing_skills


def test_complete_tree_is_ok(tmp_path: Path):
    root = _tree(
        tmp_path,
        template=(
            "# T\n\n## Enabled skills\n\n- alpha\n\n## Routines\n\n- one — first\n"
        ),
    )
    lint = lint_template(root)
    assert lint.ok is True
    assert lint.missing_skills == []
    assert lint.missing_routines == []


def test_missing_template_is_ok_and_empty(tmp_path: Path):
    lint = lint_template(tmp_path)
    assert lint.ok is True


def test_shipped_template_resolves_every_entry():
    lint = lint_template(find_repo_root())
    assert lint.missing_skills == []
    assert lint.missing_routines == []
    assert lint.ok is True
