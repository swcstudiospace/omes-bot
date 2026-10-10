# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Parse the tool-roster YAML: tool names under `tools:`, in roster order."""

from __future__ import annotations

from pathlib import Path


def roster_names(text: str) -> list[str]:
    """Tool names under the `tools:` key of the roster YAML."""
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
        if line.strip() and not line.startswith(("#", " ")):
            break
    return names


def load_roster_names(path: Path | str) -> list[str]:
    """Read the roster YAML at `path` (UTF-8) and return its tool names."""
    return roster_names(Path(path).read_text(encoding="utf-8"))


__all__ = ["load_roster_names", "roster_names"]
