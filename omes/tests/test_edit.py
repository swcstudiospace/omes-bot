"""Phase 8: the edit pipeline — exact apply, reject, and deterministic repair."""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from omes.tools.coding import register_coding_tools
from omes.tools.offer import offered_schemas
from omes.tools.registry import ToolRegistry

OMES = Path(__file__).resolve().parents[1]
ROSTER = OMES / "contracts" / "tool-rosters" / "omes.yaml"


def _registry(root: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_coding_tools(registry, root)
    return registry


def _load(payload: str) -> dict:
    return json.loads(payload)


def _diff(original: str, desired: str, name: str = "code.txt") -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(True),
            desired.splitlines(True),
            fromfile=name,
            tofile=name,
        )
    )


def test_edit_file_applies_a_well_formed_diff(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    original = "alpha\nbeta\ngamma\n"
    desired = "alpha\nBETA\ngamma\n"
    target = root / "code.txt"
    target.write_bytes(original.encode("utf-8"))

    applied = _load(
        registry.dispatch("edit_file", {"path": "code.txt", "diff": _diff(original, desired)})
    )

    assert applied["applied"] is True
    assert applied["method"] == "exact"
    assert "error" not in applied
    assert target.read_bytes() == desired.encode("utf-8")


def test_edit_file_rejects_a_bad_hunk_without_touching_the_file(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    target = root / "code.txt"
    target.write_bytes(b"alpha\nbeta\ngamma\n")
    before = target.read_bytes()
    diff = _diff("alpha\nbeta\ngamma\n", "alpha\nBETA\ngamma\n")
    diff = diff.replace("-beta\n", "-no-such-line-anywhere\n")

    rejected = _load(registry.dispatch("edit_file", {"path": "code.txt", "diff": diff}))

    assert rejected["error"] == "hunk context does not match"
    assert target.read_bytes() == before


def test_edit_file_repairs_wrong_line_numbers_by_unique_context(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    lines = [f"line-{index}\n" for index in range(1, 31)]
    original = "".join(lines)
    desired_lines = list(lines)
    desired_lines[24] = "LINE-25\n"
    desired = "".join(desired_lines)
    target = root / "code.txt"
    target.write_bytes(original.encode("utf-8"))
    diff = _diff(original, desired)
    wrong_header = diff.splitlines(True)[2]
    assert wrong_header.startswith("@@")
    shifted = "@@ -2,7 +2,7 @@\n"
    repaired_diff = diff.replace(wrong_header, shifted, 1)

    applied = _load(
        registry.dispatch("edit_file", {"path": "code.txt", "diff": repaired_diff})
    )

    assert applied["applied"] is True
    assert applied["method"] == "offset"
    assert target.read_bytes() == desired.encode("utf-8")


def test_edit_file_repairs_whitespace_only_context_differences(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    original = "def f():\n    value = 1\n    return value\n"
    desired = "def f():\n    value = 2\n    return value\n"
    target = root / "code.txt"
    target.write_bytes(original.encode("utf-8"))
    diff = _diff(original, desired)
    # The hunk claims tab indentation the file does not have.
    fuzzy_diff = diff.replace("-    value = 1\n", "-\tvalue = 1\n")

    applied = _load(
        registry.dispatch("edit_file", {"path": "code.txt", "diff": fuzzy_diff})
    )

    assert applied["applied"] is True
    assert applied["method"] == "fuzzy"
    assert target.read_bytes() == desired.encode("utf-8")


def test_edit_file_never_guesses_an_ambiguous_repair(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    target = root / "code.txt"
    target.write_bytes(b"same\nsame\nsame\nsame\n")
    before = target.read_bytes()
    diff = "@@ -9,3 +9,3 @@\n same\n-same\n+CHANGED\n same\n"

    rejected = _load(registry.dispatch("edit_file", {"path": "code.txt", "diff": diff}))

    assert rejected["error"] == "hunk context does not match"
    assert target.read_bytes() == before


def test_edit_file_applies_a_second_hunk_that_needs_repair(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    original_lines = [f"line-{index}\n" for index in range(1, 41)]
    desired_lines = list(original_lines)
    desired_lines[1] = "LINE-2\n"
    desired_lines[30] = "LINE-31\n"
    original = "".join(original_lines)
    desired = "".join(desired_lines)
    target = root / "code.txt"
    target.write_bytes(original.encode("utf-8"))
    diff = _diff(original, desired, name="code.txt")
    headers = [line for line in diff.splitlines(True) if line.startswith("@@")]
    assert len(headers) == 2
    skewed = diff.replace(headers[1], "@@ -12,7 +12,7 @@\n", 1)

    applied = _load(registry.dispatch("edit_file", {"path": "code.txt", "diff": skewed}))

    assert applied["applied"] is True
    assert applied["method"] == "offset"
    assert target.read_bytes() == desired.encode("utf-8")


def _roster_names(text: str) -> list[str]:
    names: list[str] = []
    in_tools = False
    for line in text.splitlines():
        if line.startswith("tools:"):
            in_tools = True
            continue
        if not in_tools:
            continue
        if line.startswith("  - "):
            names.append(line[4:].strip())
            continue
        if line.strip() and not line.startswith("#") and not line.startswith(" "):
            break
    return names


def test_roster_offers_edit_file(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    registry = _registry(root)
    offered = offered_schemas(
        registry, _roster_names(ROSTER.read_text(encoding="utf-8"))
    )
    names = [item["function"]["name"] for item in offered]

    assert "edit_file" in names
