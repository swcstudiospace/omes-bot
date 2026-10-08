"""Phase 44: public-repo surface stays complete, linked, and placeholder-free."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from xml.dom import minidom

OMEGA_PRIME = Path(__file__).resolve().parents[1]
ROOT = OMEGA_PRIME.parent

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "VENDOR.md",
    ".editorconfig",
    ".gitattributes",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/workflows/supply-chain.yml",
    "assets/icon.svg",
    "assets/banner.svg",
    "docs/adr/0001-prime-merge-architecture.md",
    "docs/connectors.md",
    "docs/agent-loop.md",
    "docs/migration.md",
)

PLACEHOLDERS = ("TODO", "FIXME", "your-email", "your-name", "example.com", "CHANGEME")

_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")


def test_required_files_exist_and_nontrivial() -> None:
    for name in REQUIRED_FILES:
        path = ROOT / name
        assert path.is_file(), f"missing {name}"
        assert len(path.read_text(encoding="utf-8")) > 80, f"{name} is trivially short"


def test_readme_links_resolve() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = [match for match in _LINK.findall(text) if "://" not in match]
    assert targets, "README names no relative links"
    for target in targets:
        assert (ROOT / target).exists(), f"README links missing {target}"


def test_brand_assets_referenced() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/banner.svg" in readme
    docs_front = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert docs_front.splitlines()[0].startswith("# ")
    assert "../assets/banner.svg" in docs_front


def test_svgs_valid_and_self_contained() -> None:
    for name in ("assets/icon.svg", "assets/banner.svg"):
        raw = (ROOT / name).read_text(encoding="utf-8")
        root = minidom.parseString(raw).documentElement
        assert root is not None
        assert root.tagName == "svg"
        assert root.getAttribute("width") and root.getAttribute("height")
        assert not root.getElementsByTagName("script")
        assert "href" not in raw and "xlink" not in raw
        without_ns = raw.replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert "http://" not in without_ns and "https://" not in without_ns


def test_packaging_is_public_complete() -> None:
    parsed = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = parsed["project"]
    assert project["license"] == {"text": "AGPL-3.0-only"}
    assert project["readme"] == "README.md"
    assert project["authors"] == [{"name": "Spectrum Web Co"}]
    for key in ("Homepage", "Repository", "Documentation", "Issues", "Changelog"):
        assert project["urls"][key].startswith(
            "https://github.com/swcstudiospace/omega-prime"
        )
    assert project["dependencies"] and "dependencies" not in project["urls"]
    find = parsed["tool"]["setuptools"]["packages"]["find"]
    assert find["include"] == ["omega_prime*"]
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Copyright (C) 2026 Spectrum Web Co" in license_text


def test_new_v10_modules_carry_spdx_headers() -> None:
    """REPO-01: source files created in v10 carry the AGPL SPDX header."""
    v10_modules = (
        "omega_prime/config.py",
        "omega_prime/agent/rlm.py",
        "omega_prime/agent/refine.py",
        "omega_prime/agent/goals.py",
        "omega_prime/agent/autonomous.py",
        "omega_prime/agent/messaging.py",
        "omega_prime/agent/degraded.py",
        "omega_prime/cron/heartbeat.py",
        "omega_prime/learning/harness.py",
        "omega_prime/tools/rlm.py",
        "omega_prime/tools/harness.py",
        "omega_prime/tools/goals.py",
        "omega_prime/tools/heartbeat.py",
        "omega_prime/tools/autonomous.py",
        "omega_prime/tools/agent_message.py",
        "omega_prime/prime/__init__.py",
        "omega_prime/prime/errors.py",
        "omega_prime/prime/types.py",
        "omega_prime/prime/rlm.py",
        "omega_prime/prime/harness.py",
        "omega_prime/prime/goals.py",
        "omega_prime/prime/autonomous.py",
        "omega_prime/prime/messaging.py",
    )
    for name in v10_modules:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert text.startswith(
            "# SPDX-License-Identifier: AGPL-3.0-only\n# Copyright (C) 2026 Spectrum Web Co\n"
        ), f"{name} missing the SPDX header"


def test_dependabot_and_supply_chain_cover_both_ecosystems() -> None:
    """REPO-04: dependabot (pip + actions) and pip-audit; cargo-deny lives in
    the rust-parity workflow against the pinned prime-agent workspace."""
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: pip" in dependabot
    assert "package-ecosystem: github-actions" in dependabot
    supply = (ROOT / ".github" / "workflows" / "supply-chain.yml").read_text(
        encoding="utf-8"
    )
    assert "pip_audit" in supply or "pip-audit" in supply
    assert "requirements-lock.txt" in supply
    assert "--ignore-vuln PYSEC-2026-4114" in supply
    rust = (ROOT / ".github" / "workflows" / "rust-parity.yml").read_text(
        encoding="utf-8"
    )
    assert "cargo deny" in rust or "cargo-deny" in rust


def test_no_placeholders_in_public_files() -> None:
    checked = [*list(REQUIRED_FILES), "pyproject.toml", ".gitignore"]
    for name in checked:
        text = (ROOT / name).read_text(encoding="utf-8")
        for token in PLACEHOLDERS:
            assert token not in text, f"{name} contains placeholder {token}"


def test_changelog_sections() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in text
    assert "## [0.1.0]" in text
