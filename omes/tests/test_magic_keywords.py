"""Phase 34: magic keywords ported from Omp."""

from __future__ import annotations

from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.magic_keywords import (
    MAGIC_KEYWORDS,
    MagicKeywordSettings,
    contains_magic_keyword,
    mask_non_prose,
    notices_for_turn,
)
from omes.agent.model import ScriptedModel


def test_table_has_the_three_words():
    assert [(kw.id, kw.word, kw.requires) for kw in MAGIC_KEYWORDS] == [
        ("ultrathink", "ultrathink", ()),
        ("orchestrate", "orchestrate", ("delegate_task",)),
        ("workflow", "workflowz", ("delegate_task",)),
    ]


def test_matching_follows_omp_rules():
    assert contains_magic_keyword("ultrathink about this", "ultrathink")
    assert contains_magic_keyword("please orchestrate, then verify", "orchestrate")
    assert contains_magic_keyword('"workflowz" the review', "workflowz")
    assert not contains_magic_keyword("Ultrathink this", "ultrathink")
    assert not contains_magic_keyword("we orchestrated yesterday", "orchestrate")
    assert not contains_magic_keyword("see orchestrate.ts", "orchestrate")
    assert not contains_magic_keyword("foo::orchestrate did it", "orchestrate")
    assert not contains_magic_keyword("call orchestrate() now", "orchestrate")
    assert not contains_magic_keyword("open a/b-orchestrate/c", "orchestrate")
    assert not contains_magic_keyword("re-orchestrate the plan", "orchestrate")


def test_code_and_markup_are_ignored():
    assert not contains_magic_keyword("```\nultrathink\n```", "ultrathink")
    assert not contains_magic_keyword("~~~\norchestrate\n~~~", "orchestrate")
    assert not contains_magic_keyword("run `workflowz` now", "workflowz")
    assert not contains_magic_keyword("``a workflowz b`` and done", "workflowz")
    assert contains_magic_keyword("``a `b`` and workflowz", "workflowz")
    assert not contains_magic_keyword("<note>ultrathink</note> then", "ultrathink")
    assert not contains_magic_keyword("<!-- orchestrate --> go", "orchestrate")
    assert contains_magic_keyword("```\nhidden\n```\nultrathink for real", "ultrathink")
    assert "`" not in mask_non_prose("run `x` now").replace(" ", "").replace(
        "run", ""
    ).replace("now", "")
    assert len(mask_non_prose("a `b` <c>d</c>")) == len("a `b` <c>d</c>")


def test_notices_gate_on_tools_and_switches():
    rows = notices_for_turn(
        "ultrathink and orchestrate this", {"delegate_task": object()}
    )
    assert [row["display_kind"] for row in rows] == [
        "ultrathink-notice",
        "orchestrate-notice",
    ]
    assert all(row["role"] == "user" for row in rows)
    assert "Multi-step reasoning" in rows[0]["content"]
    assert "delegate_task" in rows[1]["content"]
    gated = notices_for_turn("orchestrate and workflowz this", {})
    assert gated == []
    assert (
        "delegate_task"
        in notices_for_turn("workflowz this", {"delegate_task": object()})[0]["content"]
    )
    off = notices_for_turn(
        "ultrathink this",
        {"delegate_task": object()},
        MagicKeywordSettings(enabled=False),
    )
    assert off == []
    per_id = notices_for_turn(
        "ultrathink and orchestrate this",
        {"delegate_task": object()},
        MagicKeywordSettings(per_id={"ultrathink": False}),
    )
    assert [row["display_kind"] for row in per_id] == ["orchestrate-notice"]


def test_loop_injects_notices_for_the_turn_only():
    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(
        model=model, tools={"delegate_task": lambda **k: "ok"}, max_iterations=2
    )
    result = run_conversation(agent, "workflowz the tests")
    kinds = [m.get("display_kind") for m in result["messages"]]
    assert "workflow-notice" in kinds
    assert result["messages"][1] == {"role": "user", "content": "workflowz the tests"}

    plain = Agent(
        model=ScriptedModel([{"role": "assistant", "content": "done"}]),
        tools={"delegate_task": lambda **k: "ok"},
        max_iterations=2,
    )
    followed = run_conversation(plain, "just do it")
    assert all(m.get("display_kind") is None for m in followed["messages"])

    disabled = Agent(
        model=ScriptedModel([{"role": "assistant", "content": "done"}]),
        tools={"delegate_task": lambda **k: "ok"},
        max_iterations=2,
        magic_keywords=MagicKeywordSettings(enabled=False),
    )
    quiet = run_conversation(disabled, "ultrathink hard")
    assert all(m.get("display_kind") is None for m in quiet["messages"])
