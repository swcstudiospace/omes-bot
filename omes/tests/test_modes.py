"""Phase 10: sessions, tasks, modes, extensions, autolearn, and controls."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.extensions import ExtensionHooks
from omes.agent.model import ScriptedModel
from omes.agent.modes import PLAN_MODE_BLOCKED, apply_plan_mode
from omes.agent.security import screen_argv
from omes.learning.advisor import advise, format_advisories
from omes.learning.autolearn import Autolearn
from omes.learning.goals import GoalStore
from omes.session.persist import load_session, load_task, save_session, save_task
from omes.skills_runtime.manager import skill_view
from omes.tools.exec_jobs import JobControl


def _tool_call(name: str, arguments: str = "{}", call_id: str = "call-1") -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    }


def test_saved_session_and_task_load_on_a_later_run(tmp_path: Path):
    store = tmp_path / "store"
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    session_path = save_session(store, "s1", messages, {"model": "fake"})
    task_path = save_task(store, "t1", "Fix it", status="doing", notes="halfway")

    assert Path(session_path).is_file()
    assert Path(task_path).is_file()

    session = load_session(store, "s1")
    task = load_task(store, "t1")
    assert session["messages"] == messages
    assert session["metadata"] == {"model": "fake"}
    assert task["title"] == "Fix it"
    assert task["status"] == "doing"
    assert task["notes"] == "halfway"

    with pytest.raises(KeyError):
        load_session(store, "nope")
    with pytest.raises(KeyError):
        load_task(store, "nope")
    with pytest.raises(ValueError):
        save_task(store, "t2", "Bad", status="vibing")


def test_plan_mode_rejects_a_write_and_keeps_reads(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("original", encoding="utf-8")
    writes = []

    def write_file(path: str, content: str) -> str:
        writes.append((path, content))
        target.write_text(content, encoding="utf-8")
        return "written"

    def read_file(path: str) -> str:
        return target.read_text(encoding="utf-8")

    assert "write_file" in PLAN_MODE_BLOCKED
    assert "read_file" not in PLAN_MODE_BLOCKED

    tools = {"write_file": write_file, "read_file": read_file}
    model = ScriptedModel(
        [
            _tool_call("write_file", '{"path": "note.txt", "content": "changed"}'),
            _tool_call("read_file", '{"path": "note.txt"}'),
            {"role": "assistant", "content": "done"},
        ]
    )
    agent = Agent(model=model, tools=tools, max_iterations=6, plan_mode=True)
    result = run_conversation(agent, "change it, then read it")

    assert agent.tools is tools
    assert writes == []
    assert target.read_text(encoding="utf-8") == "original"
    rows = [row for row in result["messages"] if row.get("role") == "tool"]
    assert rows[0]["content"] == "error: plan mode forbids write_file"
    assert rows[0]["is_error"] is True
    assert rows[1]["content"] == "original"
    assert rows[1].get("is_error") is not True


def test_apply_plan_mode_keeps_unblocked_identities():
    def read_file():
        return "r"

    def write_file():
        return "w"

    wrapped = apply_plan_mode({"read_file": read_file, "write_file": write_file})

    assert wrapped["read_file"] is read_file
    assert wrapped["write_file"]() == "error: plan mode forbids write_file"


def test_extension_hook_runs_before_the_model_call():
    seen = []
    hooks = ExtensionHooks()

    def annotate(messages, tools):
        seen.append(len(messages))
        messages.append({"role": "user", "content": "extension-note"})

    hooks.register_before_model(annotate)
    model = ScriptedModel([{"role": "assistant", "content": "done"}])
    agent = Agent(model=model, tools={}, max_iterations=4, extensions=hooks)
    result = run_conversation(agent, "ping")

    assert result["final_response"] == "done"
    assert seen == [2]
    assert model.seen[0][-1] == {"role": "user", "content": "extension-note"}


def test_first_extension_stop_wins_and_skips_the_model():
    ran = []
    hooks = ExtensionHooks()
    hooks.register_before_model(
        lambda messages, tools: (ran.append("first"), {"stop": True, "reason": "ext"})[1]
    )
    hooks.register_before_model(
        lambda messages, tools: ran.append("second") or {"stop": True}
    )
    model = ScriptedModel([{"role": "assistant", "content": "never"}])
    agent = Agent(model=model, tools={}, max_iterations=4, extensions=hooks)
    result = run_conversation(agent, "ping")

    assert ran == ["first"]
    assert model.call_count == 0
    assert result["turn_exit_reason"] == "ext"


def test_autolearn_writes_through_the_skill_manager(tmp_path: Path):
    skills = tmp_path / "skills"
    learner = Autolearn(skills, min_tool_calls=2)

    skipped = learner.consider_turn(0, "latin", "# latin\n")
    assert skipped == {"learned": False, "reason": "fewer than 2 tool calls"}
    assert not skills.exists()

    nouns = "---\nname: latin\ndescription: Latin help.\n---\n# latin\n\nDecline nouns.\n"
    verbs = "---\nname: latin\ndescription: Latin help.\n---\n# latin\n\nDecline verbs.\n"
    first = learner.consider_turn(2, "latin", nouns)
    assert first == {"learned": True, "skill": "latin"}
    viewed = json.loads(skill_view("latin", skills_root=skills))
    assert "Decline nouns." in viewed["content"]

    second = learner.consider_turn(3, "latin", verbs)
    assert second == {"learned": True, "skill": "latin"}
    updated = json.loads(skill_view("latin", skills_root=skills))
    assert "Decline verbs." in updated["content"]


def test_goals_track_an_objective_with_steps(tmp_path: Path):
    store = GoalStore(tmp_path / "goals")
    store.set_objective("Ship it")
    store.add_step("Write")
    store.add_step("Test")
    store.complete_step(0)

    status = store.status()
    assert status["objective"] == "Ship it"
    assert status["steps"] == [
        {"text": "Write", "done": True},
        {"text": "Test", "done": False},
    ]

    reopened = GoalStore(tmp_path / "goals")
    assert reopened.status() == status

    with pytest.raises(IndexError):
        store.complete_step(9)


def test_advisor_renders_escaped_blocks():
    rendered = format_advisories(
        [
            {"note": "Fix <this> & that", "severity": "concern"},
            {"note": "Ship it", "severity": "blocker", "advisor": 'qa"x'},
        ]
    )

    assert rendered.splitlines() == [
        '<advisory severity="concern">Fix &lt;this&gt; &amp; that</advisory>',
        '<advisory severity="blocker" advisor="qa&quot;x">Ship it</advisory>',
    ]

    one = advise("Tidy", severity="nit")
    assert one["rendered"] == '<advisory severity="nit">Tidy</advisory>'

    with pytest.raises(ValueError):
        format_advisories([{"note": "x", "severity": "yikes"}])


def test_job_control_runs_polls_and_kills(tmp_path: Path):
    jobs = JobControl(tmp_path)

    quick = jobs.start([sys.executable, "-c", "print('hi')"])
    done = jobs.wait(quick, timeout=10)
    assert done["running"] is False
    assert done["exit_code"] == 0
    assert done["stdout"] == "hi\n"
    assert jobs.wait(quick)["stdout"] == "hi\n"

    with pytest.raises(ValueError, match="job refused"):
        jobs.start(["sudo", "true"])

    sleeper = jobs.start([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert jobs.poll(sleeper)["running"] is True
    finally:
        killed = jobs.kill(sleeper)
    assert killed["running"] is False

    with pytest.raises(KeyError):
        jobs.poll("job-999")


def test_screen_argv_refuses_danger_and_accepts_plain():
    assert screen_argv(["sudo", "true"]) == {"ok": False, "reason": "refused binary: sudo"}
    assert screen_argv(["rm", "-rf", "/"])["ok"] is False
    assert screen_argv(["rm", "--no-preserve-root", "x"])["ok"] is False
    assert screen_argv(["echo", "a\x00b"])["ok"] is False
    assert screen_argv("not-a-list")["ok"] is False
    assert screen_argv([sys.executable, "-c", "print(1)"]) == {"ok": True}
