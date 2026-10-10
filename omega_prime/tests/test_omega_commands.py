# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Slash commands and workflows. No model, no network, no gate suite."""

from __future__ import annotations

import json
import sys

from omega_prime.commands import execute_command, parse_omega_command
from omega_prime.commands.workflows import seed_memory
from omega_prime.tools.omega_command import register_omega_command_tools
from omega_prime.tools.registry import ToolRegistry


class RecordingRegistry:
    """Dispatch stand-in. ``script`` is a queue of JSON-ready dicts."""

    def __init__(self, script: list[dict] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.script = list(script or [])

    def dispatch(self, name: str, arguments: dict) -> str:
        self.calls.append((name, dict(arguments)))
        if self.script:
            return json.dumps(self.script.pop(0))
        return json.dumps({"ok": True})


def test_parse_accepts_only_a_whole_command() -> None:
    assert parse_omega_command("please /omega-help") is None
    assert parse_omega_command("/omega-help") == ("omega-help", "")
    assert parse_omega_command("  /omega-recall ships  ") == ("omega-recall", "ships")
    assert parse_omega_command("/OMEGA-Doctor") == ("omega-doctor", "")


def test_help_lists_the_catalog() -> None:
    body = execute_command("/omega-help", RecordingRegistry(), {})
    names = [row["name"] for row in body["result"]["commands"]]
    assert body["ok"] is True
    assert names == [
        "omega-help",
        "omega-doctor",
        "omega-roster",
        "omega-recall",
        "omega-retain",
        "omega-gates",
        "omega-python",
        "omega-delegate",
        "omega-workflow",
        "omega-onboard",
        "omega-connectors",
        "omega-desk",
    ]


def test_unknown_command_does_not_dispatch() -> None:
    registry = RecordingRegistry()
    body = execute_command("/omega-nope", registry, {})
    assert body["ok"] is False
    assert body["error"] == "unknown_command"
    assert "omega-help" in body["commands"]
    assert registry.calls == []


def test_retain_refuses_a_secret_before_dispatch() -> None:
    registry = RecordingRegistry()
    secret = "X_API_TOKEN=abc"
    body = execute_command(f"/omega-retain {secret}", registry, {})
    encoded = json.dumps(body)
    assert body["error"] == "secret_refused"
    assert registry.calls == []
    assert secret not in encoded
    assert "abc" not in encoded


def test_retain_tags_ordinary_text() -> None:
    registry = RecordingRegistry([{"success": True}])
    body = execute_command("/omega-retain the desk ships on Friday", registry, {})
    assert body["ok"] is True
    name, arguments = registry.calls[0]
    assert name == "memory"
    assert arguments["content"].startswith("[hindsight:omega-prime-lead] ")
    assert "Friday" in arguments["content"]


def test_connectors_never_echo_a_token() -> None:
    token = "super-secret-value"
    env = {"X_API_TOKEN": token, "ASC_KEY_ID": "only-one"}
    body = execute_command("/omega-connectors", RecordingRegistry(), env)
    encoded = json.dumps(body)
    configured = [row["id"] for row in body["result"]["configured"]]
    requested = [row["id"] for row in body["result"]["requests"]]
    assert "x" in configured
    assert "telegram" in requested
    assert "appstore" in requested
    assert token not in encoded
    assert "only-one" not in encoded


def test_python_clean_stops_after_a_failed_ruff() -> None:
    registry = RecordingRegistry([{"exit_code": 2, "stdout": "", "stderr": "nope"}])
    body = execute_command("/omega-python", registry, {})
    assert body["ok"] is False
    assert body["error"] == "workflow_failed"
    assert len(registry.calls) == 1
    argv = registry.calls[0][1]["argv"]
    assert argv == [sys.executable, "-m", "ruff", "check", "."]
    assert registry.calls[0][1]["timeout"] == 120


def test_onboard_continues_after_a_doctor_error_and_seeds() -> None:
    registry = RecordingRegistry(
        [
            {"error": "approval required", "tool": "lead_doctor"},
            {"seats": []},
            {"success": True},
        ]
    )
    body = execute_command("/omega-onboard", registry, {})
    assert body["ok"] is True
    names = [call[0] for call in registry.calls]
    assert names == ["lead_doctor", "lead_roster_status", "memory"]
    steps = body["result"]["steps"]
    assert steps[0]["ok"] is False
    assert steps[-1]["name"] == "connectors"
    assert any(row["id"] == "telegram" for row in steps[-1]["result"]["requests"])


def test_seed_dispatches_again_when_called_twice() -> None:
    registry = RecordingRegistry([{"success": True}, {"success": True}])
    first = seed_memory(registry)
    second = seed_memory(registry)
    assert first["success"] is True
    assert second["success"] is True
    assert len(registry.calls) == 2
    assert "slash command" in registry.calls[0][1]["content"]


def test_registered_tool_runs_help() -> None:
    registry = ToolRegistry()
    assert register_omega_command_tools(registry, {}) == ["omega_command"]
    raw = registry.dispatch("omega_command", {"command": "/omega-help"})
    body = json.loads(raw)
    names = [row["name"] for row in body["result"]["commands"]]
    assert body["ok"] is True
    assert "omega-onboard" in names
