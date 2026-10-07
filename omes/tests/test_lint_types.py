"""Phase 47: lint + format + typecheck configuration stays declared and enforced."""

from __future__ import annotations

import tomllib
from pathlib import Path

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_ruff_config_is_explicit() -> None:
    tool = _pyproject()["tool"]
    ruff = tool["ruff"]
    assert ruff["target-version"] == "py311"
    assert ruff["line-length"] == 88
    selected = tool["ruff"]["lint"]["select"]
    for rule in ("F", "I", "UP", "B", "SIM", "RUF"):
        assert rule in selected
    assert "E501" in tool["ruff"]["lint"]["ignore"]
    assert tool["ruff"]["lint"]["isort"]["known-first-party"] == ["omes"]


def test_mypy_config_is_hermetic_and_pip_only() -> None:
    mypy = _pyproject()["tool"]["mypy"]
    assert mypy["python_version"] == "3.11"
    assert mypy["check_untyped_defs"] is True
    assert mypy["ignore_missing_imports"] is True


def test_dev_extra_pins_the_gates_exactly() -> None:
    dev = _pyproject()["project"]["optional-dependencies"]["dev"]
    assert any(item.startswith("ruff==") for item in dev)
    assert any(item.startswith("mypy==") for item in dev)


def test_ci_runs_lint_format_and_types() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python3 -m ruff check omes/" in workflow
    assert "python3 -m ruff format --check omes/" in workflow
    assert "python3 -m mypy omes/" in workflow
    assert "pip install -e .[dev]" in workflow


def test_canonical_mcp_spellings_in_server() -> None:
    server = (OMES / "mcp_server.py").read_text(encoding="utf-8")
    assert "is_error=is_error" in server
    assert "input_schema=" in server
    assert "isError=" not in server
    assert "inputSchema=" not in server
