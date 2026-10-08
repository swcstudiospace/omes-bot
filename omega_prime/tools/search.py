"""Literal text search under a workspace root.

Adapted from Hermes ``tools/file_operations_search.py``. The query is a literal
string, not a regular expression. Matching paths are relative to the root.
A symlink that resolves outside the root is not walked and is not returned.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from omega_prime.tools.file_ops import (
    PathError,
    contains,
    require_directory,
    resolve_inside,
)


def search_text(root: str | Path, query: str, path: str = ".") -> dict[str, Any]:
    """Return relative paths of files under ``root`` whose UTF-8 text contains ``query``."""
    if not isinstance(query, str) or query == "":
        return {"error": "query must be a non-empty string"}
    try:
        base = require_directory(root)
        start = resolve_inside(base, path)
    except PathError as exc:
        return {"error": str(exc)}
    if start.is_file():
        candidates = [start]
    elif start.is_dir():
        candidates = _files_under(base, start)
    else:
        return {"paths": []}
    matches: list[str] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not contains(base, resolved) or not resolved.is_file():
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if query in text:
            matches.append(resolved.relative_to(base).as_posix())
    return {"paths": sorted(set(matches))}


def _files_under(root: Path, start: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
        current = Path(dirpath)
        kept: list[str] = []
        for name in dirnames:
            child = current / name
            if child.is_symlink() and not contains(root, child):
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            found.append(current / name)
    return found


__all__ = ["search_text"]
