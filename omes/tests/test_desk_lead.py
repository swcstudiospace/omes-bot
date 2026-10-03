"""Phase 26-02: lead pass routine over the intake queue."""

from __future__ import annotations

from omes.routines.desk_lead import run_lead_pass
from omes.tools.lead import IntakeStore
from omes.tools.todo import TodoStore, todo_read


def _receipt() -> dict:
    return {
        "commands": [{"cmd": "true", "exit_code": 0}],
        "claims": [{"claim": "done", "evidence_command_index": 0}],
        "unverified": [],
    }


def test_pass_shape_and_report(tmp_path):
    intake = IntakeStore(tmp_path / "intake.json")
    intake.submit("fix login")
    intake.submit("polish copy")
    todos = TodoStore()
    outcome = run_lead_pass(intake, lambda ticket: {"receipt": _receipt()}, todos=todos)
    assert [t["status"] for t in outcome["tickets"]] == ["done", "done"]
    assert len(outcome["receipts"]) == 2 and outcome["invalid"] == []
    assert outcome["report"].startswith("2/2 tickets done.")
    assert [t["status"] for t in todo_read(todos)["todos"]] == ["done", "done"]
    assert intake.counts() == {"done": 2}


def test_limit_bounds_the_batch(tmp_path):
    intake = IntakeStore(tmp_path / "intake.json")
    for ask in ("a", "b", "c"):
        intake.submit(ask)
    outcome = run_lead_pass(intake, lambda ticket: {"receipt": _receipt()}, limit=2)
    assert len(outcome["tickets"]) == 2
    assert intake.counts() == {"done": 2, "open": 1}


def test_no_dispatcher_blocks_and_reopens(tmp_path):
    intake = IntakeStore(tmp_path / "intake.json")
    record = intake.submit("fix login")
    outcome = run_lead_pass(intake)
    assert outcome["tickets"][0]["status"] == "blocked"
    assert outcome["tickets"][0]["reason"] == "no dispatcher"
    assert intake.get(record["intake_id"])["status"] == "open"
    assert "0/1 tickets done." in outcome["report"]


def test_missing_and_invalid_receipts_block(tmp_path):
    intake = IntakeStore(tmp_path / "intake.json")
    intake.submit("no receipt")
    intake.submit("bad receipt")
    calls = {"n": 0}

    def dispatch(ticket):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"note": "forgot the receipt"}
        return {"receipt": {"commands": [], "claims": [{"claim": "x", "evidence_command_index": 9}], "unverified": []}}

    outcome = run_lead_pass(intake, dispatch)
    assert [t["status"] for t in outcome["tickets"]] == ["blocked", "blocked"]
    assert outcome["receipts"] == []
    assert len(outcome["invalid"]) == 1
    assert intake.counts() == {"open": 2}
