"""Phase 18: the engagement sweep drafts replies without publishing."""

from __future__ import annotations

from pathlib import Path

import pytest

from omega_prime.providers.fake import FakeTransport
from omega_prime.routines.sweep import load_sweep, sweep_mentions
from omega_prime.tools.x import XClient


def _mentions_script(ids: list[str]) -> list[dict]:
    return [
        {
            "data": [
                {"id": mention_id, "text": f"hello {mention_id}"} for mention_id in ids
            ],
            "meta": {"result_count": len(ids)},
        }
    ]


def test_sweep_drafts_one_reply_per_mention(tmp_path: Path):
    transport = FakeTransport(script=_mentions_script(["m1", "m2", "m3"]))
    client = XClient(transport, token="fake")

    result = sweep_mentions(
        client,
        lambda mention: f"reply to {mention['id']}",
        directory=tmp_path,
        sweep_id="morning",
        user_id="bot-9",
    )

    assert [(draft["reply_to"], draft["text"]) for draft in result["drafts"]] == [
        ("m1", "reply to m1"),
        ("m2", "reply to m2"),
        ("m3", "reply to m3"),
    ]
    assert result["total"] == 3
    state = load_sweep(tmp_path, "morning")
    assert state is not None
    assert state["drafted"] == ["m1", "m2", "m3"]
    assert len(state["drafts"]) == 3
    assert all(call[0] == "GET" for call in transport.calls)


def test_sweep_resumes_without_duplicating_drafts(tmp_path: Path):
    first = FakeTransport(script=_mentions_script(["m1", "m2", "m3"]))
    attempts: list[str] = []

    def flaky(mention: dict) -> str:
        attempts.append(mention["id"])
        if mention["id"] == "m2":
            raise RuntimeError("crash")
        return f"reply to {mention['id']}"

    with pytest.raises(RuntimeError, match="crash"):
        sweep_mentions(
            XClient(first, token="fake"),
            flaky,
            directory=tmp_path,
            sweep_id="s1",
            user_id="bot-9",
        )
    assert attempts == ["m1", "m2"]
    first_state = load_sweep(tmp_path, "s1")
    assert first_state is not None and first_state["drafted"] == ["m1"]

    second = FakeTransport(script=_mentions_script(["m1", "m2", "m3"]))
    result = sweep_mentions(
        XClient(second, token="fake"),
        lambda mention: f"reply to {mention['id']}",
        directory=tmp_path,
        sweep_id="s1",
        user_id="bot-9",
    )

    assert [draft["mention_id"] for draft in result["drafts"]] == ["m2", "m3"]
    assert result["total"] == 3
    final_state = load_sweep(tmp_path, "s1")
    assert final_state is not None and final_state["drafted"] == ["m1", "m2", "m3"]


def test_sweep_skips_blank_drafts_once(tmp_path: Path):
    transport = FakeTransport(script=_mentions_script(["m1", "m2"]))
    result = sweep_mentions(
        XClient(transport, token="fake"),
        lambda mention: "" if mention["id"] == "m1" else "thanks!",
        directory=tmp_path,
        sweep_id="s2",
        user_id="bot-9",
    )

    assert result["skipped"] == ["m1"]
    assert [draft["mention_id"] for draft in result["drafts"]] == ["m2"]

    again = FakeTransport(script=_mentions_script(["m1", "m2"]))
    rerun = sweep_mentions(
        XClient(again, token="fake"),
        lambda mention: "thanks!",
        directory=tmp_path,
        sweep_id="s2",
        user_id="bot-9",
    )
    assert rerun["drafts"] == []
    assert rerun["skipped"] == []
    assert rerun["total"] == 1
