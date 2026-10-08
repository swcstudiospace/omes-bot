"""Data-driven eval runner. Scripted turns, structural assertions, no judge.

Golden cases replay turns through `run_conversation` and assert persona
behavior. Red-team cases assert the machinery refuses: policy escapes,
unapproved publishing-shaped exfiltration, and injected tool output that
must never self-execute. Every expectation type is structural, so runs are
bit-for-bit deterministic.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.model import ScriptedModel
from omega_prime.policy.policy import SeatPolicy
from omega_prime.tools.approvals import ApprovalLog
from omega_prime.tools.registry import ToolRegistry


def run_case(case: dict, workdir: Path) -> dict:
    """Run one case. Collect every failure; never raise for a bad case."""
    case_id = case.get("id", "<missing-id>") if isinstance(case, dict) else "<bad-case>"
    failures: list[str] = []
    try:
        _check_case(case)
    except ValueError as exc:
        return {"id": case_id, "passed": False, "failures": [str(exc)]}
    try:
        if case.get("registry"):
            outcome = _run_registry_case(case, workdir)
        else:
            outcome = _run_loop_case(case, workdir)
    except Exception as exc:
        return {"id": case_id, "passed": False, "failures": [f"case raised: {exc}"]}
    for expectation in case["expect"]:
        try:
            failure = _check(expectation, outcome)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if failure is not None:
            failures.append(failure)
    return {"id": case_id, "passed": not failures, "failures": failures}


def run_suite(cases_dir: str | Path, workdir: str | Path) -> dict:
    """Run `golden.json` + `redteam.json`. Return the aggregate report."""
    root = Path(cases_dir)
    work = Path(workdir)
    results: list[dict] = []
    for name in ("golden.json", "redteam.json"):
        path = root / name
        try:
            cases = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            results.append(
                {
                    "id": name,
                    "passed": False,
                    "failures": [f"cannot load {name}: {exc}"],
                }
            )
            continue
        if not isinstance(cases, list):
            results.append(
                {"id": name, "passed": False, "failures": [f"{name} is not a list"]}
            )
            continue
        for index, case in enumerate(cases):
            case_dir = work / f"{path.stem}-{index}"
            case_dir.mkdir(parents=True, exist_ok=True)
            results.append(run_case(case, case_dir))
    passed = sum(1 for result in results if result["passed"])
    return {"passed": passed, "failed": len(results) - passed, "results": results}


def main(argv: list[str] | None = None) -> int:
    """`python3 -m omega_prime.evals.runner [cases_dir]`. Exit 0 when all pass."""
    args = list(sys.argv[1:] if argv is None else argv)
    cases_dir = Path(args[0]) if args else Path(__file__).resolve().parent / "cases"
    with tempfile.TemporaryDirectory(prefix="omega-prime-evals-") as tmp:
        report = run_suite(cases_dir, Path(tmp))
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {result['id']}")
        for failure in result["failures"]:
            print(f"  - {failure}")
    print(f"{report['passed']} passed, {report['failed']} failed")
    return 0 if report["failed"] == 0 else 1


def _check_case(case: Any) -> None:
    if not isinstance(case, dict):
        raise ValueError("case must be an object")
    if not isinstance(case.get("id"), str) or not case["id"]:
        raise ValueError("case needs a non-empty string id")
    if not isinstance(case.get("expect"), list) or not case["expect"]:
        raise ValueError(f"case {case['id']}: expect must be a non-empty list")
    if case.get("registry"):
        if not isinstance(case.get("tool"), str):
            raise ValueError(f"case {case['id']}: registry cases need a tool name")
    else:
        if not isinstance(case.get("script"), list) or not case["script"]:
            raise ValueError(f"case {case['id']}: loop cases need a script")
        if not isinstance(case.get("user"), str):
            raise ValueError(f"case {case['id']}: loop cases need a user string")


def _run_loop_case(case: dict, workdir: Path) -> dict:
    calls: list[str] = []
    tools: dict[str, Any] = {}
    for name, canned in (case.get("tools") or {}).items():
        tools[name] = _stub(name, canned, calls)
    model = ScriptedModel(case["script"])
    agent = Agent(model=model, tools=tools, max_iterations=8)
    result = run_conversation(agent, case["user"])
    return {"result": result, "calls": calls, "workdir": workdir}


def _run_registry_case(case: dict, workdir: Path) -> dict:
    log = ApprovalLog()
    policy = None
    if isinstance(case.get("policy"), dict):
        policy = SeatPolicy(case["policy"])
    registry = ToolRegistry(approval_log=log, policy=policy)
    if case.get("approve") is True:
        approved = log.approve(case["tool"], case.get("approved_by", "ada"))
        if not approved.get("approved"):
            raise ValueError("eval setup could not approve the tool")
    if case.get("family") == "ultrathink":
        return _run_ultrathink_family_case(case, workdir, registry)
    if "family" in case:
        raise ValueError(f"case {case['id']}: unknown family {case['family']!r}")
    calls: list[str] = []
    canned = case.get("returns", "ok")
    registry.register(
        case["tool"],
        "eval tool",
        {"type": "object", "properties": {}},
        _stub(case["tool"], canned, calls),
        requires_approval=bool(case.get("requires_approval")),
    )
    payload = json.loads(registry.dispatch(case["tool"], case.get("arguments", {})))
    return {"payload": payload, "calls": calls, "workdir": workdir}


def _run_ultrathink_family_case(
    case: dict, workdir: Path, registry: ToolRegistry
) -> dict:
    """Dispatch through real ultrathink registration with a hermetic runner.

    Approval flags come from production ``register_ultrathink_tools`` (which
    reads ``APPROVAL_TOOLS``), never from the case's ``requires_approval``.
    The injected CLI runner records argv, returns deterministic JSON echoing
    the dispatched state/mark, and never spawns a subprocess or network call.
    ``calls`` maps one entry per runner invocation so ``tool_called`` proves
    the handler ran and ``tool_not_called`` proves zero runner calls on
    refusal.
    """
    from omega_prime.tools.ultrathink import (
        UltrathinkClient,
        UltrathinkContext,
        register_ultrathink_tools,
    )

    runner_argv: list[list[str]] = []

    def _fake_run(argv: list[str], timeout: int = 120) -> dict[str, Any]:
        items = list(argv)
        runner_argv.append(items)
        try:
            state_value = items[items.index("--state") + 1]
        except (ValueError, IndexError):
            state_value = ""
        mark_value = items[-1] if items else ""
        return {
            "exit_code": 0,
            "stdout": json.dumps(
                {"ok": True, "state": state_value, "mark": mark_value}
            ),
            "stderr": "",
        }

    client = UltrathinkClient(UltrathinkContext(root="eval-hermetic", run=_fake_run))
    register_ultrathink_tools(registry, client)
    payload = json.loads(registry.dispatch(case["tool"], case.get("arguments", {})))
    calls = [case["tool"] for _ in runner_argv]
    return {"payload": payload, "calls": calls, "workdir": workdir}


def _stub(name: str, canned: Any, calls: list[str]) -> Any:
    def _run(*args: Any, **kwargs: Any) -> Any:
        calls.append(name)
        return canned

    return _run


def _check(expectation: Any, outcome: dict) -> str | None:
    """Return a failure string, or None when the expectation holds."""
    if not isinstance(expectation, dict) or not isinstance(
        expectation.get("type"), str
    ):
        raise ValueError("expectation needs a string type")
    kind = expectation["type"]
    result = outcome.get("result", {})
    messages = result.get("messages", []) if isinstance(result, dict) else []
    final = result.get("final_response", "") if isinstance(result, dict) else ""
    calls = outcome.get("calls", [])
    payload = outcome.get("payload", {})

    if kind == "final_contains":
        return (
            None
            if expectation["text"] in final
            else f"final lacks {expectation['text']!r}"
        )
    if kind == "final_not_contains":
        return (
            None
            if expectation["text"] not in final
            else f"final leaks {expectation['text']!r}"
        )
    if kind == "exit_reason":
        reason = result.get("turn_exit_reason")
        return (
            None
            if reason == expectation["reason"]
            else f"exit {reason!r} != {expectation['reason']!r}"
        )
    if kind == "tool_called":
        return (
            None
            if expectation["name"] in calls
            else f"{expectation['name']} was not called"
        )
    if kind == "tool_not_called":
        return (
            None
            if expectation["name"] not in calls
            else f"{expectation['name']} was called"
        )
    if kind == "refusal_contains":
        for row in messages:
            if (
                isinstance(row, dict)
                and row.get("role") == "tool"
                and expectation["text"] in str(row.get("content", ""))
            ):
                return None
        if expectation["text"] in str(payload.get("error", "")):
            return None
        return f"no refusal mentions {expectation['text']!r}"
    if kind == "payload_contains":
        blob = json.dumps(payload, ensure_ascii=False)
        wanted = expectation.get("text", "")
        return None if wanted in blob else f"payload lacks {wanted!r}"
    if kind == "tool_rows":
        count = sum(
            1 for row in messages if isinstance(row, dict) and row.get("role") == "tool"
        )
        return (
            None
            if count == expectation["count"]
            else f"{count} tool rows != {expectation['count']}"
        )
    raise ValueError(f"unknown expectation type: {kind}")


if __name__ == "__main__":
    raise SystemExit(main())
