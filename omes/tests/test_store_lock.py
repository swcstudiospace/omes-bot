"""Phase 42, LOCK-01: no direct GreptimeDB/TimescaleDB/DragonflyDB clients.

Omes reaches the backing stores only through substrate-mcp. This test fails
the build if `omes/` grows a direct client:

- Layer 1 (import guard): no DB/redis driver imports anywhere.
- Layer 2 (endpoint guard): no backing-store endpoint literals anywhere
  (only this file is exempt, since it states the patterns).

Sanctioned exception: `SystemsContext.timescale`/`greptime` are injected
query callables (dependency inversion, no sockets, no URLs, default `None`).
Both defaults are asserted below so the exception cannot silently widen.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

OMES = Path(__file__).resolve().parents[1]

BANNED_IMPORT_TOPS = frozenset(
    {
        "aioredis",
        "asyncpg",
        "dragonfly",
        "greptime",
        "greptimedb",
        "influxdb",
        "pg8000",
        "psycopg",
        "psycopg2",
        "questdb",
        "redis",
    }
)

ENDPOINT_PATTERNS = (
    re.compile(
        r"(?i)(greptime|timescale|dragonfly)[a-z0-9.-]*\.(railway\.internal|up\.railway\.app)"
    ),
    re.compile(r"(?i)\bredis://"),
    re.compile(r":6379\b"),
    re.compile(r":4000\b"),
)


def _py_files() -> list[Path]:
    return sorted(OMES.rglob("*.py"))


def _top_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        names = [alias.name.split(".")[0] for alias in node.names]
        return names[0] if names else None
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module.split(".")[0]
    return None


def test_no_driver_imports() -> None:
    offenders: list[str] = []
    for path in _py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            offenders.append(f"{path.relative_to(OMES)}: unparsable ({exc})")
            continue
        for node in ast.walk(tree):
            top = _top_name(node)
            if top in BANNED_IMPORT_TOPS:
                offenders.append(f"{path.relative_to(OMES)}: imports {top}")
    assert offenders == []


def test_no_backing_store_endpoints() -> None:
    offenders: list[str] = []
    for path in _py_files():
        if path == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            offenders.append(f"{path.relative_to(OMES)}: unreadable ({exc})")
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in ENDPOINT_PATTERNS:
                if pattern.search(line):
                    offenders.append(
                        f"{path.relative_to(OMES)}:{lineno}: {line.strip()[:100]}"
                    )
    assert offenders == []


def test_injected_seams_stay_unconfigured_by_default() -> None:
    from omes.tools.systems import SystemsContext

    ctx = SystemsContext()
    assert ctx.timescale is None
    assert ctx.greptime is None
