"""Production turns journal, and durable_status reports it."""

from __future__ import annotations

import json
from pathlib import Path

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.delegate import delegate_task
from omega_prime.agent.model import ScriptedModel
from omega_prime.cron.scheduler import JobStore, run_due_jobs
from omega_prime.durable.journal import GuardedJournal, TurnJournal
from omega_prime.tools.durable_surface import register_durable_surface_tools
from omega_prime.tools.registry import ToolRegistry


def test_cron_job_writes_a_journal(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "cron" / "jobs.json")
    now = 1_700_000_000
    store.schedule("say hi", now)
    model = ScriptedModel([{"role": "assistant", "content": "hello"}])
    ran = run_due_jobs(store, now, model, {})
    assert ran[0]["last_result"] == "hello"
    journal = TurnJournal(tmp_path / "cron" / "turns.sqlite")
    assert journal.status()["entry_count"] >= 1


def test_delegate_child_writes_the_parent_journal(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "turns.sqlite")
    parent = type("Parent", (), {})()
    parent.child_model = ScriptedModel([{"role": "assistant", "content": "done"}])
    parent.tools = {}
    parent.delegate_depth = 0
    parent.journal = journal
    body = json.loads(delegate_task(parent, "ship it"))
    assert body["summary"] == "done"
    assert journal.status()["entry_count"] >= 1


def test_journal_failure_emits_and_the_turn_finishes() -> None:
    class _Boom(TurnJournal):
        def __init__(self) -> None:
            self.path = Path("unused")

        def begin_run(self, run_id: str) -> None:
            raise OSError("disk full")

        def append(self, run_id: str, row: dict) -> None:
            raise OSError("disk full")

        def finish_run(
            self, run_id: str, status: str, final_response: str = ""
        ) -> None:
            raise OSError("disk full")

    agent = Agent(
        model=ScriptedModel([{"role": "assistant", "content": "still here"}]),
        tools={},
    )

    def sink(**fields: object) -> None:
        from omega_prime.agent.harness import emit

        event_type = fields.pop("type", "prime_degraded")
        emit(agent, str(event_type), **fields)

    agent.journal = GuardedJournal(_Boom(), sink)
    result = run_conversation(agent, "go")
    assert result["final_response"] == "still here"
    from omega_prime.agent.harness import events_of

    assert any(event["type"] == "prime_degraded" for event in events_of(agent))


def test_durable_status_reports_a_journal(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "cron" / "jobs.json")
    now = 1_700_000_000
    store.schedule("say hi", now)
    run_due_jobs(
        store,
        now,
        ScriptedModel([{"role": "assistant", "content": "noted"}]),
        {},
    )
    registry = ToolRegistry()
    register_durable_surface_tools(registry, tmp_path)
    body = json.loads(registry.dispatch("durable_status", {}))
    assert body["journal"] == "present"
    assert body["entry_count"] >= 1
    assert body["last_run_id"]
