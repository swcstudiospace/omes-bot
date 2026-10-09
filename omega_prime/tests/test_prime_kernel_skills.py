# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Load pinned Prime skill packages without copying them."""

from __future__ import annotations

import asyncio
import sys

from omega_prime.prime_kernel.skills import PrimeSkillError, list_skills, load_skill


def test_list_skills_marks_edit_importable_and_factory_markdown_only():
    by_name = {row["name"]: row for row in list_skills()}
    assert by_name["edit"] == {"name": "edit", "importable": True, "package": "edit"}
    # factory/ contains only SKILL.md; there is no src package.
    assert by_name["factory"]["importable"] is False
    assert by_name["factory"]["package"] is None
    names = [row["name"] for row in list_skills()]
    assert names == sorted(names)


def test_load_skill_edit_replaces_a_unique_string(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("alpha", encoding="utf-8")
    edit = load_skill("edit")

    message = asyncio.run(edit.run(str(target), "alpha", "beta"))

    assert target.read_text(encoding="utf-8") == "beta"
    assert "Edited" in message


def test_load_skill_missing_names_the_skill():
    try:
        load_skill("missing")
    except (PrimeSkillError, FileNotFoundError) as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("load_skill('missing') did not raise")


def test_list_skills_does_not_import_attach_image():
    already = "attach_image" in sys.modules
    list_skills()
    if not already:
        assert "attach_image" not in sys.modules
