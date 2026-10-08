"""Assemble the single Omega Prime seat prompt.

Prepend prompts/_shared/core-directives.xml to prompts/bot-00-omega-prime.xml and
write prompts-assembled/OMEGA_PRIME.xml. Substitutes {{DEFAULT_BRANCH}}, {{BOT_ID}},
and {{ROSTER_VERSION}} from the roster JSON. A leftover {{...}} is an error.

The template may name a skill or a routine only when that file exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_:]+\}\}")
BULLET_RE = re.compile(r"^-\s+([a-z0-9][a-z0-9-]*)\b")

SEAT_SOURCE = "bot-00-omega-prime.xml"
SEAT_NAME = "OMEGA_PRIME"
ROSTER_KEYS = ("bot_id", "default_branch", "roster_version")


def package_root() -> Path:
    return Path(__file__).resolve().parent


def load_roster(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"assemble-prompts: cannot read roster {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise SystemExit(f"assemble-prompts: roster {path} is not an object")
    missing = [key for key in ROSTER_KEYS if key not in document]
    if missing:
        raise SystemExit(f"assemble-prompts: roster {path} lacks {', '.join(missing)}")
    return document


def substitute(text: str, roster: dict) -> str:
    values = {
        "{{DEFAULT_BRANCH}}": str(roster["default_branch"]),
        "{{BOT_ID}}": str(roster["bot_id"]),
        "{{ROSTER_VERSION}}": str(roster["roster_version"]),
    }
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def unfilled(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        found.extend((line_no, match) for match in PLACEHOLDER_RE.findall(line))
    return found


def render(root: Path, roster_path: Path) -> str:
    roster = load_roster(roster_path)
    core_path = root / "prompts" / "_shared" / "core-directives.xml"
    body_path = root / "prompts" / SEAT_SOURCE
    if not core_path.is_file():
        raise SystemExit(f"assemble-prompts: missing {core_path}")
    if not body_path.is_file():
        raise SystemExit(f"assemble-prompts: missing {body_path}")
    text = substitute(core_path.read_text(encoding="utf-8"), roster).rstrip()
    text += "\n" + substitute(body_path.read_text(encoding="utf-8"), roster)
    if not text.endswith("\n"):
        text += "\n"
    left = unfilled(text)
    if left:
        where = "; ".join(f"{name} at line {line_no}" for line_no, name in left[:5])
        raise SystemExit(f"assemble-prompts: unfilled placeholder(s): {where}")
    return text


def assembled_path(root: Path) -> Path:
    return root / "prompts-assembled" / f"{SEAT_NAME}.xml"


def write_assembled(root: Path, text: str) -> Path:
    destination = assembled_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def section_bullets(template: str, heading: str) -> list[str]:
    lines = template.splitlines()
    start = None
    marker = f"## {heading}"
    for index, line in enumerate(lines):
        if line.strip() == marker:
            start = index + 1
            break
    if start is None:
        raise SystemExit(f"assemble-prompts: template missing section {heading!r}")
    names: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        match = BULLET_RE.match(line.strip())
        if match:
            names.append(match.group(1))
    return names


def template_gaps(root: Path, template: Path | None = None) -> list[str]:
    """Return repo-relative paths the template names that are not on disk."""
    path = template or (root / "grokbot" / "templates" / "OMEGA_PRIME.md")
    text = path.read_text(encoding="utf-8")
    gaps: list[str] = []
    for name in section_bullets(text, "Enabled skills"):
        skill = root / "skills" / name / "SKILL.md"
        if not skill.is_file():
            gaps.append(str(skill.relative_to(root)))
    for name in section_bullets(text, "Routines"):
        routine = root / "routines" / f"{name}.md"
        if not routine.is_file():
            gaps.append(str(routine.relative_to(root)))
    return gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="assemble-prompts")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--roster", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    root = (args.root or package_root()).resolve()
    roster_path = (
        args.roster or (root / "grokbot" / "rosters" / "default.json")
    ).resolve()
    if not roster_path.is_file():
        raise SystemExit(f"assemble-prompts: missing roster {roster_path}")

    text = render(root, roster_path)
    gaps = template_gaps(root)
    if gaps:
        for gap in gaps:
            print(f"  - {gap}", file=sys.stderr)
        raise SystemExit(
            "assemble-prompts: template names a skill or routine that is not on disk"
        )

    destination = assembled_path(root)
    if args.check:
        if not destination.is_file():
            raise SystemExit(f"assemble-prompts --check: missing {destination}")
        have = destination.read_text(encoding="utf-8")
        if have != text:
            raise SystemExit(
                "assemble-prompts --check: prompts-assembled/OMEGA_PRIME.xml differs from the sources; "
                "run scripts/assemble-prompts.sh and commit the result"
            )
        print(f"assemble-prompts --check: {SEAT_NAME} up to date")
        return 0

    write_assembled(root, text)
    print(f"wrote {destination.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
