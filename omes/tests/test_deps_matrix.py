"""Phase 48: dependency floors, lockfile, Python matrix, discord guard."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent

FLOORS = {
    "tweepy": (4, 17),
    "mcp": (2, 3),
    "pyrit": (1, 1),
    "apscheduler": (3, 11),
    "aiogram": (3, 31),
    "discord.py": (2, 7),
    "playwright": (1, 63),
    "appium-python-client": (6, 0),
}


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split("."):
        digits = "".join(char for char in piece if char.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def test_floors_are_at_verified_versions() -> None:
    parsed = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = parsed["project"]["dependencies"]
    lowered = [dep.lower() for dep in deps]
    assert "mcp>=2.3,<3" in lowered
    for name, floor in FLOORS.items():
        if name == "mcp":
            continue
        want = f"{name.lower()}>={'.'.join(str(part) for part in floor)}"
        assert want in lowered, f"missing floor {want}"


def test_installed_versions_satisfy_floors() -> None:
    for name, floor in FLOORS.items():
        installed = _version_tuple(metadata.version(name))
        assert installed >= floor, f"{name} {installed} below floor {floor}"


def test_lockfile_pins_all_direct_deps() -> None:
    lines = (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# Omes Bot verified lockfile")
    pins = {
        line.split("==")[0].lower(): line.split("==")[1]
        for line in lines
        if "==" in line and not line.startswith("#")
    }
    for name, floor in FLOORS.items():
        assert name.lower() in pins, f"lockfile misses {name}"
        assert _version_tuple(pins[name.lower()]) >= floor


def test_ci_matrix_covers_supported_pythons() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in ("verify:", "lint:", "types:"):
        assert job in workflow
    for version in ('"3.12"', '"3.13"', '"3.14"'):
        assert workflow.count(version) >= 3, f"matrix misses {version}"


def test_discord_module_imports_without_the_library() -> None:
    code = "\n".join(
        [
            "import sys",
            "sys.modules['discord'] = None",
            "import omes.tools.discord as d",
            "assert d.discord is None, 'guard did not engage'",
            "try:",
            "    d._default_client()",
            "except d.DiscordError as exc:",
            "    assert 'not importable' in str(exc)",
            "else:",
            "    raise SystemExit('factory did not fail soft')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
