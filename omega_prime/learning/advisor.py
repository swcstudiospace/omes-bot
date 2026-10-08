"""Advisor notes rendered as agent-facing blocks.

Ports ``formatAdvisorBatchContent`` from
``packages/coding-agent/src/advisor/advise-tool.ts``: one ``<advisory>``
element per note, severity as an attribute, text and attribute XML-escaped.
Advice, not orders — the renderer carries no behavior of its own.
"""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

SEVERITIES = ("nit", "concern", "blocker")


def advise(
    note: str, severity: str = "nit", advisor: str | None = None
) -> dict[str, Any]:
    """Build one note plus its rendered block."""
    if not isinstance(note, str) or note == "":
        raise ValueError("note must be a non-empty string")
    _check_severity(severity)
    if advisor is not None and (not isinstance(advisor, str) or advisor == ""):
        raise ValueError("advisor must be a non-empty string")
    entry: dict[str, Any] = {"note": note, "severity": severity}
    if advisor is not None:
        entry["advisor"] = advisor
    return {**entry, "rendered": format_advisories([entry])}


def format_advisories(notes: list[dict]) -> str:
    """Render each note as one ``<advisory>`` line."""
    lines = []
    for entry in notes:
        if not isinstance(entry, dict):
            raise ValueError("notes must be dicts")
        note = entry.get("note")
        if not isinstance(note, str) or note == "":
            raise ValueError("note must be a non-empty string")
        severity = entry.get("severity", "nit")
        _check_severity(severity)
        advisor = entry.get("advisor")
        if advisor is not None and (not isinstance(advisor, str) or advisor == ""):
            raise ValueError("advisor must be a non-empty string")
        attributes = f' severity="{_escape_attribute(severity)}"'
        if advisor is not None:
            attributes += f' advisor="{_escape_attribute(advisor)}"'
        lines.append(f"<advisory{attributes}>{escape(note)}</advisory>")
    return "\n".join(lines)


def _check_severity(severity: Any) -> None:
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {', '.join(SEVERITIES)}")


def _escape_attribute(value: str) -> str:
    return escape(value, {'"': "&quot;"})


__all__ = ["SEVERITIES", "advise", "format_advisories"]
