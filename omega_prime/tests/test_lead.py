"""Phase 26-01: lead core+lead tool families behind tmp stores and fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega_prime.credentials.redact import REDACTED
from omega_prime.memory.store import MemoryStore
from omega_prime.receipts import append_execution
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.lead import (
    LEAD_TOOL_NAMES,
    EventStore,
    IntakeStore,
    LeadClient,
    LeadContext,
    RosterStore,
    register_lead_tools,
)
from omega_prime.tools.registry import ToolRegistry

ASSEMBLE_STUB = """#!/bin/bash
mkdir -p omega_prime/prompts-assembled
printf '<seat>omega-prime-test</seat>' > omega_prime/prompts-assembled/OMEGA_PRIME.xml
"""

SEAT_PROMPT = """<agent id="bot-00-omega-prime">
<skill path="skills/lead-pack/SKILL.md" />
<skill path="skills/debugging/SKILL.md" />
</agent>
"""

OWNERSHIP = """version: 1
bots:
  bot-00-omega-prime:
    name: Omega Prime
paths:
  - pattern: "**"
    owner: bot-00-omega-prime
  - pattern: "omega_prime/skills/*"
    owner: bot-99-guest
"""


class FakeSubstrate:
    def __init__(self, content=None, error=None):
        self.calls: list[tuple] = []
        self.content = content if content is not None else {"ok": True}
        self.error = error

    def call_tool(self, name, payload, timeout=10):
        self.calls.append((name, payload, timeout))
        if self.error:
            return {"error": self.error[0], "reason": self.error[1]}
        return {"content": self.content}

    def emit(self, event):
        self.calls.append(("emit", event))
        if self.error:
            return {"error": self.error[0], "reason": self.error[1]}
        return {"body": {"accepted": True}}


class FakeBus:
    def __init__(self):
        self.calls: list[tuple] = []

    def start_job(self, runtime, goal, provider, key):
        self.calls.append(("start", runtime, goal, provider, key))
        return {"body": {"job_id": "job-1", "wsUrl": "wss://x"}}

    def wait_job(self, job_id, timeout_sec, poll_sec):
        self.calls.append(("wait", job_id, timeout_sec, poll_sec))
        return {"body": {"job_id": job_id, "state": "done"}}


def _ctx(tmp_path: Path, **overrides) -> LeadContext:
    root = tmp_path / "root"
    (root / "omega_prime" / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "omega_prime" / "prompts" / "bot-00-omega-prime.xml").write_text(
        SEAT_PROMPT, encoding="utf-8"
    )
    (root / "omega_prime" / "ownership.yaml").write_text(OWNERSHIP, encoding="utf-8")
    script = root / "omega_prime" / "scripts" / "assemble-prompts.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    script.write_text(ASSEMBLE_STUB, encoding="utf-8")
    script.chmod(0o755)
    base: dict[str, Any] = dict(
        root=root,
        memory=MemoryStore(tmp_path / "memory"),
        intake=IntakeStore(tmp_path / "intake.json"),
        roster=RosterStore(tmp_path / "roster.json"),
        events=EventStore(tmp_path / "events.ndjson"),
    )
    base.update(overrides)
    return LeadContext(**base)


def _good_receipt() -> dict:
    return {
        "commands": [{"cmd": "true", "exit_code": 0}],
        "claims": [{"claim": "done", "evidence_command_index": 0}],
        "unverified": [],
    }


def test_intake_claim_ack_round_trip(tmp_path: Path):
    client = LeadClient(_ctx(tmp_path))
    intake = client.ctx.intake
    assert intake is not None
    assert client.intake_next()["work_order"] is None
    first = intake.submit(
        "fix login", origin="github", links=["https://github.com/o/r/issues/7"]
    )
    intake.submit("polish copy", origin="local")
    claimed = client.intake_next()
    assert claimed["work_order"]["intake_id"] == first["intake_id"]
    assert claimed["work_order"]["status"] == "in_progress"
    assert claimed["queue"] == {"in_progress": 1, "open": 1}
    assert "ORIGINAL" in claimed["next"]
    second = client.intake_next(origin="local")["work_order"]
    assert second["ask"] == "polish copy"

    notes: list[tuple] = []

    def _notify(url: str, body: dict) -> bool:
        notes.append((url, body))
        return True

    client.ctx.notify = _notify
    acked = client.intake_ack(
        first["intake_id"],
        "done",
        graph_id="g-1",
        message="shipped",
        links=["https://github.com/o/r/issues/7"],
    )
    assert acked["ok"] is True
    assert acked["intake"]["status"] == "done"
    assert acked["notify"]["delivered"] is True
    assert "Graph ID: `g-1`" in notes[0][1]
    assert "intake `in-" in notes[0][1]

    local = client.intake_ack(second["intake_id"], "done")
    assert local["notify"] == {"delivered": False, "reason": "origin has no callback"}
    assert "not_found" in client.intake_ack("in-missing", "done")["error"]

    store = intake
    stranded = store.submit("stuck work")
    store.next(None, "gone-worker", now=1000.0)
    stuck = store.get(stranded["intake_id"])
    assert stuck is not None and stuck["status"] == "in_progress"
    assert store.next(None, "new-worker", now=1000.0) is None
    reclaimed = store.next(None, "new-worker", now=1000.0 + 3601.0)
    assert reclaimed is not None
    assert reclaimed["intake_id"] == stranded["intake_id"]
    assert store.release(stranded["intake_id"]) is True
    reopened = store.get(stranded["intake_id"])
    assert reopened is not None and reopened["status"] == "open"
    assert store.release("in-missing") is False


def test_graph_and_bus_passthrough_and_unconfigured(tmp_path: Path):
    substrate = FakeSubstrate(content={"graph": "ok"})
    bus = FakeBus()
    client = LeadClient(_ctx(tmp_path, substrate=substrate, bus=bus))
    registered = client.graph_register(
        "g-1", "o/r", [{"node_id": "n1", "linear_id": "L-2"}]
    )
    assert registered == {"ok": True, "graph_id": "g-1", "substrate": {"graph": "ok"}}
    name, payload, timeout = substrate.calls[0]
    assert name == "graph_register" and timeout == 10
    assert payload["nodes"] == [
        {"node_id": "n1", "linear_identifier": "L-2", "state": "open"}
    ]

    done = client.graph_state("g-1", "n1", "complete", note="all green")
    assert done["action"] == "complete"
    assert substrate.calls[1][1]["result"] == {
        "summary": "all green",
        "tests_pass": False,
    }
    assert substrate.calls[1][1]["session_id"] == "grok-bot:lead:g-1"

    started = client.bus_start("local", "run tests", provider="p", idempotency_key="k")
    assert started == {"ok": True, "job": {"job_id": "job-1"}}
    assert bus.calls[0] == ("start", "local", "run tests", "p", "k")
    waited = client.bus_wait("job-1")
    assert waited["job"]["state"] == "done" and waited["timed_out"] is False

    bare = LeadClient(_ctx(tmp_path))
    assert "not_configured" in bare.graph_register("g", "r")["error"]
    assert "not_configured" in bare.graph_state("g", "n", "claim")["error"]
    assert "not_configured" in bare.bus_start("r", "g")["error"]
    assert "not_configured" in bare.bus_wait("j")["error"]
    assert "not_configured" in bare.docs_search("q")["error"]


def test_roster_status_completeness(tmp_path: Path):
    client = LeadClient(_ctx(tmp_path))
    assert client.roster_status() == {
        "packs": [],
        "intake_queue": {},
        "complete": False,
    }
    roster = client.ctx.roster
    assert roster is not None
    intake = client.ctx.intake
    assert intake is not None
    roster.register("lead", {"version": 1, "tools": list(LEAD_TOOL_NAMES)})
    intake.submit("ask")
    status = client.roster_status()
    assert status["complete"] is True
    assert status["packs"][0]["pack"] == "lead"
    assert len(status["packs"][0]["tools"]) == 16
    assert status["intake_queue"] == {"open": 1}


def test_doctor_register_install_and_check(tmp_path: Path):
    registry = ToolRegistry()
    ctx = _ctx(tmp_path, registry=registry)
    client = LeadClient(ctx)
    register_lead_tools(registry, client)

    assert "invalid_args" in client.doctor("register")["error"]
    assert client.doctor("register", agent_uuid="u-1")["registered"] == ["lead"]
    installed = client.doctor("install_prompt")
    assert (
        installed["ok"] is True
        and installed["prompt"] == "<seat>omega-prime-test</seat>"
    )
    import hashlib

    sha = hashlib.sha256(b"<seat>omega-prime-test</seat>").hexdigest()
    assert installed["sha256"] == sha

    check = client.doctor(
        "check", prompt_sha256=sha, installed_skills=["lead-pack", "debugging"]
    )
    assert check["checks"]["prompt"]["green"] is True
    assert check["checks"]["skills"] == {
        "green": True,
        "declared": ["lead-pack", "debugging"],
        "missing": [],
    }
    assert check["checks"]["memory"]["green"] is True
    assert check["checks"]["tools"] == {"green": True, "pack": 16, "live": 16}
    assert check["checks"]["roster"]["green"] is True
    assert check["checks"]["substrate"]["green"] is False
    assert check["green"] is False

    bare = client.doctor("check")
    assert bare["checks"]["prompt"]["green"] is False
    assert bare["checks"]["skills"]["missing"] == ["lead-pack", "debugging"]


def test_render_prompt_refuses_placeholders(tmp_path: Path):
    ctx = _ctx(tmp_path)
    script = Path(ctx.root) / "omega_prime" / "scripts" / "assemble-prompts.sh"
    script.write_text(
        "#!/bin/bash\nmkdir -p omega_prime/prompts-assembled\nprintf '{{X}}' > omega_prime/prompts-assembled/OMEGA_PRIME.xml\n",
        encoding="utf-8",
    )
    rendered = LeadClient(ctx).render_prompt()
    assert "placeholders" in rendered["error"]
    assert (
        "not_configured"
        in LeadClient(LeadContext(root=tmp_path / "empty")).render_prompt()["error"]
    )


def test_memory_retain_and_recall(tmp_path: Path):
    client = LeadClient(_ctx(tmp_path))
    assert "evidence_required" in client.memory_retain("note")["error"]
    assert (
        "secret_refused"
        in client.memory_retain("key sk-abcdefgh1234", source="chat")["error"]
    )
    kept = client.memory_retain(
        "desk uses receipts", source="chat", tags=["core"], graph_id="g-1"
    )
    assert kept == {"ok": True, "bank": "omega-prime-lead"}
    recalled = client.memory_recall("receipts")
    assert recalled["banks"] == ["omega-prime-lead", "omega-prime-desk"]
    assert any(
        "desk uses receipts" in entry for entry in recalled["results"][0]["entries"]
    )
    assert client.memory_recall("nothing-here")["results"][0]["entries"] == []
    assert "not_configured" in LeadClient(LeadContext()).memory_recall("q")["error"]


def test_receipt_check_paths(tmp_path: Path, monkeypatch: Any):
    monkeypatch.setenv("OMEGA_PRIME_COMMAND_LOG", str(tmp_path / "command-log.jsonl"))
    append_execution("true", 0, "", cwd=str(tmp_path))
    ctx = _ctx(tmp_path)
    client = LeadClient(ctx)
    assert client.receipt_check(_good_receipt()) == {
        "ok": True,
        "bot": "bot-00-omega-prime",
    }
    bad = client.receipt_check(
        {
            "commands": [],
            "claims": [{"claim": "x", "evidence_command_index": 5}],
            "unverified": [],
        }
    )
    assert bad["ok"] is False and bad["problems"]
    leaked = dict(_good_receipt(), unverified=["token=abc123"])
    assert client.receipt_check(leaked)["problems"] == [
        "receipt contains a credential shape (PD-4)"
    ]
    assert "invalid_args" in client.receipt_check()["error"]
    assert "not_found" in client.receipt_check(receipt_path="nope.json")["error"]
    (Path(ctx.root) / "r.json").write_text("not json", encoding="utf-8")
    assert "invalid_receipt" in client.receipt_check(receipt_path="r.json")["error"]
    (Path(ctx.root) / "good.json").write_text(
        json.dumps(_good_receipt()), encoding="utf-8"
    )
    assert client.receipt_check(receipt_path="good.json")["ok"] is True


def test_ownership_last_match_wins_and_unowned(tmp_path: Path):
    client = LeadClient(_ctx(tmp_path))
    result = client.ownership_resolve(
        ["omega_prime/agent/loop.py", "omega_prime/skills/x/SKILL.md"]
    )
    assert result["results"][0] == {
        "path": "omega_prime/agent/loop.py",
        "owner": "bot-00-omega-prime",
        "mine": True,
        "unowned": False,
    }
    assert result["results"][1]["owner"] == "bot-99-guest"
    assert result["results"][1]["mine"] is False
    (Path(client.ctx.root) / "omega_prime" / "ownership.yaml").write_text(
        "version: 1\npaths: []\n", encoding="utf-8"
    )
    lonely = client.ownership_resolve(["x.py"])
    assert lonely["results"][0]["unowned"] is True


def test_events_size_cap_audit_and_emit(tmp_path: Path):
    emitted: list[dict] = []

    class Emitter:
        def emit(self, event):
            emitted.append(event)
            return {"body": {"accepted": True}}

    client = LeadClient(_ctx(tmp_path, substrate=FakeSubstrate()))
    client.ctx.substrate.emit = Emitter().emit
    assert (
        "payload_too_large"
        in client.event_emit("note", payload={"blob": "x" * 5000})["error"]
    )
    outcome = client.event_emit("ticketed", payload={"ticket": "t-1"}, graph_id="g-1")
    assert outcome["ok"] is True and emitted and emitted[0]["kind"] == "ticketed"
    events = client.ctx.events
    assert events is not None
    rows = events.records()
    assert rows[0]["payload"] == {"ticket": "t-1"} and rows[0]["seq"] == 1

    token = "ghp_" + "x" * 36
    nested = client.event_emit("ticketed", payload={"meta": {"client_secret": token}})
    assert nested["ok"] is True
    assert events.records()[-1]["payload"] == {"meta": {"client_secret": REDACTED}}
    assert emitted[-1]["payload"] == {"meta": {"client_secret": REDACTED}}

    (tmp_path / "b").mkdir()
    local = LeadClient(_ctx(tmp_path / "b"))
    stored_only = local.event_emit("note")
    assert stored_only["emitted"] is False and stored_only["stored"]["seq"] == 1

    (tmp_path / "c").mkdir()
    failing = LeadClient(
        _ctx(tmp_path / "c", substrate=FakeSubstrate(error=("upstream_error", "down")))
    )
    assert failing.event_emit("note")["local_mirror"] is True


def test_brief_cache_docs_search_and_approvals(tmp_path: Path):
    ctx = _ctx(
        tmp_path,
        docs_index=lambda q, limit, repo: [
            {"content": "c" * 2000, "document": "d", "dataset_id": "k", "score": 0.9}
        ],
    )
    client = LeadClient(ctx)
    first = client.brief(task_id="t-1")
    assert first["reminders"] and first["loaded_packs"] == [] and "cached" not in first
    second = client.brief(task_id="t-1")
    assert second["cached"] is True
    assert client.brief(task_id="t-1", refresh=True).get("cached") is None
    docs = client.docs_search("receipts")
    assert len(docs["results"][0]["content"]) == 1500
    assert "not a repository fact" in docs["note"]

    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log)
    register_lead_tools(registry, client)
    assert json.loads(registry.dispatch("lead_roster_status", {}))["complete"] is False
    assert json.loads(
        registry.dispatch("lead_bus_start", {"runtime": "r", "goal": "g"})
    ) == {"error": "approval required", "tool": "lead_bus_start"}
    assert "error" in json.loads(
        registry.dispatch("lead_memory_retain", {"content": ""})
    )
    assert log.approve("lead_event_emit", "ada").get("approved") is True
    assert json.loads(registry.dispatch("lead_event_emit", {"kind": "k"}))["ok"] is True
