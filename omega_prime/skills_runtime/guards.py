"""Refuse a skill write that would escape the root or break SKILL.md.

No PyYAML. Frontmatter is a ``---`` block of flat ``key: value`` lines.
Create caps the description at 60 characters. Edit and patch do not.
"""

from __future__ import annotations

import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
CREATE_DESCRIPTION_LIMIT = 60
MAX_CONTENT_CHARS = 100_000

_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


def validate_name(name: str) -> str | None:
    """Error text when ``name`` is not one safe path segment, else None."""
    if not isinstance(name, str) or name == "":
        return "Skill name is required."
    if (
        name != name.strip()
        or ".." in name
        or "/" in name
        or "\\" in name
        or Path(name).is_absolute()
    ):
        return f"Invalid skill name '{name}'."
    if len(name) > MAX_NAME_LENGTH or NAME_RE.fullmatch(name) is None:
        return (
            f"Invalid skill name '{name}'. "
            "Use lowercase letters, numbers, hyphens, dots, and underscores. "
            f"Length must be 1..{MAX_NAME_LENGTH}."
        )
    return None


def validate_category(category: str | None) -> str | None:
    """Error text when ``category`` is set and is not one safe path segment."""
    if category is None:
        return None
    if not isinstance(category, str):
        return "Category must be a string."
    if category.strip() == "":
        return None
    if (
        category != category.strip()
        or ".." in category
        or "/" in category
        or "\\" in category
        or Path(category).is_absolute()
        or len(category) > MAX_NAME_LENGTH
        or NAME_RE.fullmatch(category) is None
    ):
        return f"Invalid category '{category}'."
    return None


def validate_content_size(content: str) -> str | None:
    if not isinstance(content, str):
        return "Content must be a string."
    if len(content) > MAX_CONTENT_CHARS:
        return f"SKILL.md content is {len(content)} characters (limit: {MAX_CONTENT_CHARS})."
    return None


def validate_frontmatter(content: str, *, new_skill: bool = False) -> str | None:
    """Require ``name``, ``description``, and a non-empty body.

    ``new_skill`` applies the 60-character description cap. Edit and patch pass
    ``new_skill=False`` so an existing longer description can still be saved.
    """
    parsed, body, error = parse_frontmatter(content)
    if error is not None:
        return error
    assert parsed is not None and body is not None
    for field in ("name", "description"):
        if field not in parsed or parsed[field] == "":
            return f"Frontmatter must include '{field}'."
    description = parsed["description"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."
    if new_skill and len(description) > CREATE_DESCRIPTION_LIMIT:
        return (
            f"Description is {len(description)} characters. "
            f"New skills must be at most {CREATE_DESCRIPTION_LIMIT}."
        )
    if body.strip() == "":
        return "SKILL.md must have content after the frontmatter."
    return None


def parse_frontmatter(
    content: str,
) -> tuple[dict[str, str] | None, str | None, str | None]:
    """Return ``(mapping, body, error)``. Nested YAML is an error."""
    if not isinstance(content, str) or content.strip() == "":
        return None, None, "Content cannot be empty."
    text = content.lstrip("\ufeff")
    if not text.startswith("---"):
        return None, None, "SKILL.md must start with YAML frontmatter (---)."
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return None, None, "SKILL.md must start with YAML frontmatter (---)."
    mapping: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "".join(lines[index + 1 :])
            return mapping, body, None
        if line.strip() == "":
            continue
        if line[0] in {" ", "\t"} or ":" not in line:
            return None, None, "Frontmatter must be flat key: value lines."
        key, raw_value = line.split(":", 1)
        if _KEY_RE.fullmatch(key) is None:
            return None, None, "Frontmatter must be flat key: value lines."
        if key in mapping:
            return None, None, f"Frontmatter key '{key}' is duplicated."
        mapping[key] = _unwrap(raw_value.strip())
    return (
        None,
        None,
        "SKILL.md frontmatter is not closed. Ensure you have a closing '---' line.",
    )


def skill_directory(
    skills_root: str | Path, name: str, category: str | None = None
) -> Path:
    """Lexical skill directory under an already-resolved root."""
    root = Path(skills_root)
    segment = (
        category.strip() if isinstance(category, str) and category.strip() else None
    )
    return root / segment / name if segment else root / name


def outside_root(root: Path, path: Path) -> bool:
    """True when ``path`` resolves outside ``root``, including via a symlink."""
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return True
    try:
        path.relative_to(root)
    except ValueError:
        return True
    return False


def _unwrap(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


__all__ = [
    "CREATE_DESCRIPTION_LIMIT",
    "MAX_CONTENT_CHARS",
    "MAX_DESCRIPTION_LENGTH",
    "MAX_NAME_LENGTH",
    "NAME_RE",
    "outside_root",
    "parse_frontmatter",
    "skill_directory",
    "validate_category",
    "validate_content_size",
    "validate_frontmatter",
    "validate_name",
]
