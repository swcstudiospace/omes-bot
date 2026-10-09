"""Interactive Grok Bot Turn Emulator and Smoke Test Harness.

Enables developers and CI pipelines to simulate Grok Bot conversational turns,
tool calls, gated approval workflows, and receipt generation locally without
requiring live xAI API keys or cloud infrastructure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from omega_prime.grokbot.audit import GrokBotAuditTracer
from omega_prime.mcp_server import default_registry


@dataclass
class TurnResult:
    scenario: str
    tool_name: str
    arguments: dict[str, Any]
    status: str
    result: Any
    elapsed_ms: float
    error: str | None = None


class GrokBotTurnEmulator:
    """Emulates Grok Bot conversation turns and tool invocations."""

    def __init__(
        self, root: Path | None = None, auditor: GrokBotAuditTracer | None = None
    ) -> None:
        self.root = root or Path.cwd()
        self.auditor = auditor or GrokBotAuditTracer()
        self.registry = default_registry(root=self.root, home=Path.home())

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool invocation through the local MCP toolset."""
        start = time.time()
        try:
            if tool_name not in self.registry._tools:
                res = {"error": f"Tool '{tool_name}' not found in active roster"}
                elapsed = (time.time() - start) * 1000
                self.auditor.log_event(
                    "emulator_tool_call",
                    tool_name=tool_name,
                    caller="grok-emulator",
                    status="not_found",
                    duration_ms=elapsed,
                    is_error=True,
                    details={"arguments": arguments, "error": res["error"]},
                )
                return res

            raw_output = self.registry.dispatch(tool_name, arguments or {})
            elapsed = (time.time() - start) * 1000
            try:
                parsed_res = json.loads(raw_output)
            except Exception:
                parsed_res = raw_output

            is_err = (
                isinstance(parsed_res, dict) and parsed_res.get("error") is not None
            )
            self.auditor.log_event(
                "emulator_tool_call",
                tool_name=tool_name,
                caller="grok-emulator",
                status="error" if is_err else "ok",
                duration_ms=elapsed,
                is_error=is_err,
                details={"arguments": arguments},
            )
            return {
                "status": "error" if is_err else "ok",
                "result": parsed_res,
                "elapsed_ms": elapsed,
            }
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            self.auditor.log_event(
                "emulator_tool_call",
                tool_name=tool_name,
                caller="grok-emulator",
                status="error",
                duration_ms=elapsed,
                is_error=True,
                details={"arguments": arguments, "error": str(exc)},
            )
            return {"status": "error", "error": str(exc), "elapsed_ms": elapsed}

    def run_smoke_suite(self) -> list[TurnResult]:
        """Execute a predefined set of canonical Grok Bot smoke test turns."""
        results: list[TurnResult] = []

        scenarios: list[tuple[str, str, dict[str, Any]]] = [
            (
                "Read package init",
                "read_file",
                {"path": "__init__.py"},
            ),
            (
                "Inspect TODO list",
                "todo_read",
                {},
            ),
            (
                "Run harmless echo command",
                "run_terminal",
                {"argv": ["echo", "omega-prime-grokbot-emulator"]},
            ),
            (
                "Clarify prompt question",
                "clarify",
                {"question": "What is the next phase?"},
            ),
        ]

        for desc, tool_name, args in scenarios:
            t0 = time.time()
            out = self.execute_tool(tool_name, args)
            dur = (time.time() - t0) * 1000
            is_err = out.get("status") == "error" or "error" in out
            results.append(
                TurnResult(
                    scenario=desc,
                    tool_name=tool_name,
                    arguments=args,
                    status="ok" if not is_err else "error",
                    result=out.get("result"),
                    elapsed_ms=dur,
                    error=out.get("error"),
                )
            )

        return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grok Bot local turn emulator and smoke tester"
    )
    parser.add_argument(
        "--smoke", action="store_true", help="Run automated smoke turn suite"
    )
    parser.add_argument(
        "--tool", type=str, default=None, help="Execute a specific tool call"
    )
    parser.add_argument(
        "--args", type=str, default="{}", help="JSON arguments for tool call"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    args = parser.parse_args()

    emulator = GrokBotTurnEmulator()

    if args.tool:
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError as exc:
            print(f"Error parsing --args JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        res = emulator.execute_tool(args.tool, tool_args)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Tool: {args.tool}")
            print(f"Status: {res.get('status')}")
            if "error" in res:
                print(f"Error: {res['error']}")
            else:
                print(f"Result:\n{res.get('result')}")
        return

    if args.smoke or not args.tool:
        print("Running Grok Bot Smoke Turn Test Suite...")
        results = emulator.run_smoke_suite()
        all_ok = True
        for r in results:
            mark = "PASS" if r.status == "ok" else "FAIL"
            if r.status != "ok":
                all_ok = False
            print(f"  [{mark}] {r.scenario} ({r.tool_name}) - {r.elapsed_ms:.1f}ms")
            if r.error:
                print(f"         Error: {r.error}")

        if not all_ok:
            sys.exit(1)
        print("All smoke turn scenarios passed successfully!")


if __name__ == "__main__":
    main()
