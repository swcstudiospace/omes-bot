"""Ultrathink turn plan resolution: find this turn's plan, if any.

Probes `last-plan.json` across the host state directories (same order
as the ultrathink Grok host) and reports the plan + spec paths. A
missing file or an unreadable plan is `found: False`, never an
exception: there is simply no plan for this turn.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _candidates(env: dict[str, str]) -> list[Path]:
    home = env.get("HOME", os.path.expanduser("~"))
    grok_home = env.get("GROK_HOME", str(Path(home) / ".grok"))
    hermes_home = env.get("HERMES_HOME", str(Path(home) / ".hermes"))
    xdg = env.get("XDG_CONFIG_HOME", str(Path(home) / ".config"))
    ordered: list[str] = []
    if env.get("ULTRATHINK_STATE_DIR"):
        ordered.append(str(Path(env["ULTRATHINK_STATE_DIR"]) / "last-plan.json"))
    if env.get("GROK_PLUGIN_DATA"):
        ordered.append(str(Path(env["GROK_PLUGIN_DATA"]) / "ultrathink" / "last-plan.json"))
    ordered.extend([
        str(Path(grok_home) / "plugin-data" / "ultrathink" / "last-plan.json"),
        str(Path(hermes_home) / "ultrathink" / "last-plan.json"),
        str(Path(xdg) / "muse" / "ultrathink" / "last-plan.json"),
    ])
    if env.get("PI_CODING_AGENT_DIR"):
        ordered.append(str(Path(env["PI_CODING_AGENT_DIR"]) / "ultrathink" / "last-plan.json"))
    else:
        ordered.append(str(Path(home) / ".omp" / "agent" / "ultrathink" / "last-plan.json"))
    ordered.append(str(Path(home) / ".claude" / "ultrathink" / "last-plan.json"))
    return [Path(p) for p in ordered]


def resolve_turn_plan(*, state_dirs: list[str | Path] | None = None,
                      env: dict[str, str] | None = None) -> dict[str, Any]:
    """Return `{found, plan_path, spec_path, spec_exists}` for this turn."""
    if state_dirs is not None:
        paths = [Path(d) / "last-plan.json" for d in state_dirs]
    else:
        paths = _candidates(dict(os.environ) if env is None else env)
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            plan = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(plan, dict):
            continue
        spec_path = plan.get("specPath") if isinstance(plan.get("specPath"), str) else None
        spec_exists = bool(spec_path) and Path(spec_path).is_file()
        return {"found": True, "plan_path": str(path), "spec_path": spec_path,
                "spec_exists": spec_exists}
    return {"found": False, "plan_path": None, "spec_path": None, "spec_exists": False}
