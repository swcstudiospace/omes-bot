"""Phase 38: docs set stays linked and headed."""

from __future__ import annotations

import re
from pathlib import Path

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent
DOCS = ROOT / "docs"

_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+\.md)\)")


def test_summary_links_resolve_exactly_once():
    summary = (DOCS / "SUMMARY.md").read_text(encoding="utf-8")
    links = _LINK.findall(summary)
    assert links, "SUMMARY.md names no pages"
    assert len(links) == len(set(links)), "a page is listed twice"
    for link in links:
        assert (DOCS / link).is_file(), f"SUMMARY.md links missing {link}"
    pages = {p.name for p in DOCS.glob("*.md")} - {"SUMMARY.md"}
    assert set(links) == pages, "SUMMARY.md and docs/ disagree"


def test_sync_config_and_headings():
    config = (ROOT / ".gitbook.yaml").read_text(encoding="utf-8")
    assert "root:" in config and "./docs/" in config
    assert "structure:" in config and "SUMMARY.md" in config
    for page in sorted(DOCS.glob("*.md")):
        if page.name == "SUMMARY.md":
            continue
        first = page.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# "), f"{page.name} has no top-level heading"
