"""Phase 19: the nightly pass earns skills only for earned turns."""

from __future__ import annotations

import json
from pathlib import Path

from omes.routines.nightly import nightly_pass
from omes.skills_runtime.manager import skill_view


def _turn(turn_id: str, user_text: str, tool_output: str | None) -> dict:
    messages: list[dict] = [{"role": "user", "content": user_text}]
    if tool_output is not None:
        messages.append({"role": "tool", "name": "run", "content": tool_output})
    return {"id": turn_id, "messages": messages}


def test_nightly_pass_creates_skills_only_for_earned_turns(tmp_path: Path):
    turns = [
        _turn(
            "t1",
            "please save as a skill name:deploy the steps",
            "run ./deploy.sh --prod",
        ),
        _turn("t2", "thanks for the help", "you are welcome"),
    ]
    result = nightly_pass(tmp_path / "state", tmp_path / "skills", turns)

    assert [entry["turn_id"] for entry in result["created"]] == ["t1"]
    assert result["total_created"] == 1
    assert result["reviewed"] == ["t1", "t2"]

    viewed = json.loads(skill_view("deploy", skills_root=tmp_path / "skills"))
    assert "run ./deploy.sh --prod" in viewed["content"]

    state = json.loads(
        (tmp_path / "state" / "nightly.json").read_text(encoding="utf-8")
    )
    assert state == {"reviewed": ["t1", "t2"]}


def test_nightly_rerun_reviews_nothing_twice(tmp_path: Path):
    turns = [_turn("t1", "save as a skill name:deploy it", "output here")]
    first = nightly_pass(tmp_path / "state", tmp_path / "skills", turns)
    assert first["total_created"] == 1

    second = nightly_pass(tmp_path / "state", tmp_path / "skills", turns)
    assert second == {"created": [], "reviewed": [], "total_created": 0}
