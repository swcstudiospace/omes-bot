# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Fixed tool sequences for slash commands.

A workflow dispatches registry tools in order. It records a tool error
as that step's result. It does not replace the error with a success.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parent / "seeds" / "memory.txt"
HINDSIGHT_PREFIX = "[hindsight:omega-prime-lead] "
WORKFLOW_NAMES = ("onboard", "python-clean", "connectors", "desk")

_CONNECTORS: tuple[dict[str, Any], ...] = (
    {
        "id": "x",
        "env": ("X_API_TOKEN",),
        "mode": "all",
        "ask": "Set X_API_TOKEN on the host so the X connector can read mentions. Do not paste it into chat.",
    },
    {
        "id": "telegram",
        "env": ("TELEGRAM_BOT_TOKEN",),
        "mode": "all",
        "ask": "Set TELEGRAM_BOT_TOKEN on the host so the Telegram connector can read updates. Do not paste it into chat.",
    },
    {
        "id": "discord",
        "env": ("DISCORD_BOT_TOKEN",),
        "mode": "all",
        "ask": "Set DISCORD_BOT_TOKEN on the host so the Discord connector can read messages. Do not paste it into chat.",
    },
    {
        "id": "delegate",
        "env": ("XAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
        "mode": "any",
        "ask": "Set one of XAI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY on the host so /omega-delegate can run a child. Do not paste it into chat.",
    },
    {
        "id": "substrate",
        "env": ("SUBSTRATE_TOKEN", "SUBSTRATE_TOKEN_GROK_BOT"),
        "mode": "any",
        "ask": "Set SUBSTRATE_TOKEN or SUBSTRATE_TOKEN_GROK_BOT on the host so briefs and events can reach substrate. Do not paste it into chat.",
    },
    {
        "id": "hindsight",
        "env": ("HINDSIGHT_API_KEY", "HINDSIGHT_API_TOKEN"),
        "mode": "any",
        "ask": "Set HINDSIGHT_API_KEY or HINDSIGHT_API_TOKEN on the host for the shared episodic bank. Do not paste it into chat.",
    },
    {
        "id": "railway",
        "env": ("RAILWAY_TOKEN",),
        "mode": "all",
        "ask": "Set RAILWAY_TOKEN on the host for Railway status and logs. Do not paste it into chat.",
    },
    {
        "id": "greptile",
        "env": ("GREPTILE_API_KEY",),
        "mode": "all",
        "ask": "Set GREPTILE_API_KEY on the host for Greptile review. Do not paste it into chat.",
    },
    {
        "id": "vercel",
        "env": ("VERCEL_TOKEN",),
        "mode": "all",
        "ask": "Set VERCEL_TOKEN on the host for Vercel deployments. Do not paste it into chat.",
    },
    {
        "id": "play",
        "env": ("PLAY_CONSOLE_TOKEN",),
        "mode": "all",
        "ask": "Set PLAY_CONSOLE_TOKEN on the host for Play Console. Do not paste it into chat.",
    },
    {
        "id": "appstore",
        "env": ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_PRIVATE_KEY"),
        "mode": "all",
        "ask": "Set ASC_KEY_ID, ASC_ISSUER_ID, and ASC_PRIVATE_KEY on the host for App Store Connect. Do not paste them into chat.",
    },
)


@dataclass(frozen=True)
class Step:
    """One workflow step. ``local`` is ``seed`` or ``connectors``; otherwise ``tool`` runs."""

    name: str
    stop_on_error: bool
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    local: str | None = None


def connector_requests(env: Mapping[str, str]) -> dict[str, Any]:
    """Report connector ids from env names. Never copy env values."""
    configured: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for spec in _CONNECTORS:
        names = tuple(spec["env"])
        present = _present(env, names, str(spec["mode"]))
        row: dict[str, Any] = {"id": spec["id"], "env": list(names)}
        if present:
            configured.append(row)
        else:
            row["ask"] = spec["ask"]
            requests.append(row)
    return {"configured": configured, "requests": requests}


def seed_memory(registry: Any) -> dict[str, Any]:
    """Add the checked-in seed through the memory tool. A duplicate is the store's concern."""
    if not SEED_PATH.is_file():
        return {
            "error": "seed_missing",
            "reason": "memory seed file is not in the package",
        }
    text = SEED_PATH.read_text(encoding="utf-8").strip()
    if not text or "§" in text:
        return {
            "error": "seed_missing",
            "reason": "memory seed file is empty or unusable",
        }
    content = text if text.startswith(HINDSIGHT_PREFIX) else HINDSIGHT_PREFIX + text
    return dispatch_tool(
        registry,
        "memory",
        {"action": "add", "target": "memory", "content": content},
    )


def run_workflow(name: str, registry: Any, env: Mapping[str, str]) -> dict[str, Any]:
    """Run one named workflow. Unknown names list the catalog."""
    steps = _workflows().get(name)
    if steps is None:
        return {
            "ok": False,
            "workflow": name,
            "error": "unknown_workflow",
            "workflows": list(WORKFLOW_NAMES),
            "steps": [],
        }
    ran: list[dict[str, Any]] = []
    for step in steps:
        payload = _run_step(step, registry, env)
        ok = _step_ok(payload)
        ran.append({"name": step.name, "ok": ok, "result": payload})
        if not ok and step.stop_on_error:
            return {
                "ok": False,
                "workflow": name,
                "error": "workflow_failed",
                "steps": ran,
            }
    return {"ok": True, "workflow": name, "steps": ran}


def _workflows() -> dict[str, tuple[Step, ...]]:
    exe = sys.executable
    ruff = {
        "argv": [exe, "-m", "ruff", "check", "."],
        "timeout": 120,
    }
    compileall = {
        "argv": [exe, "-m", "compileall", "-q", "."],
        "timeout": 120,
    }
    return {
        "python-clean": (
            Step("run_terminal", True, tool="run_terminal", arguments=ruff),
            Step("run_terminal", True, tool="run_terminal", arguments=compileall),
        ),
        "onboard": (
            Step(
                "lead_doctor",
                False,
                tool="lead_doctor",
                arguments={"action": "check"},
            ),
            Step("lead_roster_status", False, tool="lead_roster_status", arguments={}),
            Step("seed_memory", False, local="seed"),
            Step("connectors", False, local="connectors"),
        ),
        "desk": (
            Step(
                "lead_doctor",
                False,
                tool="lead_doctor",
                arguments={"action": "check"},
            ),
            Step("lead_roster_status", False, tool="lead_roster_status", arguments={}),
            Step("lead_intake_next", False, tool="lead_intake_next", arguments={}),
        ),
        "connectors": (Step("connectors", False, local="connectors"),),
    }


def _run_step(step: Step, registry: Any, env: Mapping[str, str]) -> dict[str, Any]:
    try:
        if step.local == "seed":
            return seed_memory(registry)
        if step.local == "connectors":
            return connector_requests(env)
        if step.tool is None:
            return {"error": "dispatch_failed", "reason": "step has no tool"}
        return dispatch_tool(registry, step.tool, step.arguments or {})
    except Exception as exc:
        return {
            "error": "dispatch_failed",
            "reason": f"{type(exc).__name__}: {exc}",
        }


def dispatch_tool(
    registry: Any, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    from omega_prime.commands.context import get_nested_dispatch

    nested = get_nested_dispatch()
    try:
        raw = (
            nested(tool, arguments)
            if nested is not None
            else registry.dispatch(tool, arguments)
        )
    except Exception as exc:
        return {
            "error": "dispatch_failed",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "dispatch_failed", "reason": "tool result is not JSON"}
        if isinstance(parsed, dict):
            return parsed
        return {"error": "dispatch_failed", "reason": "tool result is not an object"}
    if isinstance(raw, dict):
        return raw
    return {"error": "dispatch_failed", "reason": "tool result is not an object"}


def _step_ok(payload: dict[str, Any]) -> bool:
    if payload.get("error"):
        return False
    if "exit_code" not in payload:
        return True
    code = payload["exit_code"]
    return isinstance(code, int) and not isinstance(code, bool) and code == 0


def _present(env: Mapping[str, str], names: tuple[str, ...], mode: str) -> bool:
    flags = [_filled(env, name) for name in names]
    if mode == "any":
        return any(flags)
    return all(flags)


def _filled(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name)
    return isinstance(value, str) and value.strip() != ""


__all__ = [
    "HINDSIGHT_PREFIX",
    "SEED_PATH",
    "WORKFLOW_NAMES",
    "connector_requests",
    "dispatch_tool",
    "run_workflow",
    "seed_memory",
]
