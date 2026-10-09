# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Load executable skill packages from the pinned Prime checkout.

Prime's skill sources stay in the read-only ``prime-agent/skills`` tree
described by VENDOR.md. This module imports those packages in place and
does not copy them into Omega Prime.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


class PrimeSkillError(Exception):
    """A named skill cannot be loaded from the Prime checkout."""


def skills_root() -> Path:
    """Return the pinned ``prime-agent/skills`` directory."""
    return Path(__file__).resolve().parents[2] / "prime-agent" / "skills"


def _package_name(skill_dir: Path) -> str | None:
    """Return the single importable package under ``src/``, if one exists."""
    src = skill_dir / "src"
    if not src.is_dir():
        return None
    packages = [
        child.name
        for child in src.iterdir()
        if child.is_dir() and (child / "__init__.py").is_file()
    ]
    if len(packages) != 1:
        return None
    return packages[0]


def list_skills() -> list[dict]:
    """List skill directories without importing their packages.

    Each entry has ``name`` (directory name), ``importable``, and ``package``
    (the package directory under ``src/``, or ``None``).
    """
    root = skills_root()
    rows: list[dict] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        package = _package_name(child)
        rows.append(
            {
                "name": child.name,
                "importable": package is not None,
                "package": package,
            }
        )
    return rows


def load_skill(name: str):
    """Import the package for skill directory ``name`` and return the module.

    ``name`` is the directory name (``edit``), not the Python package name.
    The skill's ``src`` directory is inserted at the front of ``sys.path``.
    """
    root = skills_root()
    skill_dir = root / name
    if not skill_dir.is_dir() or name.startswith("."):
        raise PrimeSkillError(f"skill {name!r} was not found under {root}")
    package = _package_name(skill_dir)
    if package is None:
        raise FileNotFoundError(f"skill {name!r} has no importable package under src/")
    src = str(skill_dir / "src")
    if src in sys.path:
        sys.path.remove(src)
    sys.path.insert(0, src)
    return importlib.import_module(package)
