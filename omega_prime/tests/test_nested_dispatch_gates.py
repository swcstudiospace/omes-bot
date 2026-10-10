"""Nested omega_command dispatch re-enters the host gates."""

from __future__ import annotations

import asyncio
import json

from omega_prime.commands import execute_command
from omega_prime.commands.workflows import dispatch_tool
from omega_prime.grokbot.interceptors import ToolCall, ToolDenial, ToolOutcome
from omega_prime.grokbot.ratelimit import RateLimiter, ToolRateLimitInterceptor
from omega_prime.mcp_server import call_tool_handler
from omega_prime.tools.omega_command import register_omega_command_tools
from omega_prime.tools.registry import ToolRegistry


class _Params:
    def __init__(self, name: str, arguments: dict) -> None:
        self.name = name
        self.arguments = arguments


class _Recorder:
    def __init__(self) -> None:
        self.names: list[str] = []

    def before(self, call: ToolCall) -> ToolDenial | None:
        self.names.append(call.name)
        return None

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call, outcome


def _registry() -> tuple[ToolRegistry, list[str]]:
    seen: list[str] = []
    registry = ToolRegistry()

    def lead_doctor(action: str = "check") -> dict:
        seen.append(action)
        return {"ok": True, "action": action}

    registry.register(
        "lead_doctor",
        "doctor",
        {"type": "object", "properties": {"action": {"type": "string"}}},
        lead_doctor,
    )
    register_omega_command_tools(registry, {})
    return registry, seen


def test_recording_interceptor_sees_the_inner_call() -> None:
    registry, seen = _registry()
    recorder = _Recorder()
    call = call_tool_handler(
        registry,
        ["omega_command", "lead_doctor"],
        interceptors=[recorder],
    )
    result = asyncio.run(
        call(None, _Params("omega_command", {"command": "/omega-doctor"}))
    )
    body = json.loads(result.content[0].text)
    assert body["ok"] is True
    assert seen == ["check"]
    assert recorder.names == ["omega_command", "lead_doctor"]


def test_rate_limit_denies_the_inner_call() -> None:
    registry, seen = _registry()
    limiter = ToolRateLimitInterceptor(RateLimiter(1))
    call = call_tool_handler(
        registry,
        ["omega_command", "lead_doctor"],
        interceptors=[limiter],
    )
    result = asyncio.run(
        call(None, _Params("omega_command", {"command": "/omega-doctor"}))
    )
    text = result.content[0].text
    assert "rate_limited" in text
    assert seen == []


def test_roster_omission_denies_the_inner_call() -> None:
    registry, seen = _registry()
    call = call_tool_handler(registry, ["omega_command"])
    result = asyncio.run(
        call(None, _Params("omega_command", {"command": "/omega-doctor"}))
    )
    text = result.content[0].text
    assert "policy forbids lead_doctor" in text
    assert seen == []


def test_in_process_command_skips_the_host_scope() -> None:
    registry, seen = _registry()
    body = execute_command("/omega-doctor", registry, {})
    assert body["ok"] is True
    assert seen == ["check"]


def test_nested_depth_cap_returns_an_error_dict() -> None:
    registry = ToolRegistry()

    def bottom() -> str:
        return json.dumps(dispatch_tool(registry, "bottom", {}))

    def deeper() -> str:
        return json.dumps(dispatch_tool(registry, "bottom", {}))

    def inner() -> str:
        return json.dumps(dispatch_tool(registry, "deeper", {}))

    for name, handler in (("inner", inner), ("deeper", deeper), ("bottom", bottom)):
        registry.register(
            name,
            name,
            {"type": "object", "properties": {}},
            handler,
        )
    call = call_tool_handler(registry, ["inner", "deeper", "bottom"])
    result = asyncio.run(call(None, _Params("inner", {})))
    assert "nested_dispatch_depth" in result.content[0].text
