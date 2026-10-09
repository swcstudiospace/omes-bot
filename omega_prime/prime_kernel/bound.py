# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Product calls into the PyO3 Prime bindings.

``apply_goal`` and ``apply_autonomous`` are the ``/goal`` and
``/autonomous`` commands. Parsing, limits, and goal transitions run in
``pa-core``. A missing extension raises ``ImportError``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega_prime.prime_kernel.native import load_extension

_RUNS: dict[str, Any] = {}


def apply_goal(root: str | Path, args: str) -> dict:
    """Parse ``args`` with ``parse_goal_command`` and store the wire ``GoalState``."""
    extension = load_extension()
    directory = Path(root)
    path = directory / "prime-kernel" / "goal-state.json"
    goal = extension.goals.Goal()
    if path.is_file():
        goal = extension.goals.Goal.from_wire(
            json.loads(path.read_text(encoding="utf-8"))
        )
    result = goal.apply(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result["state"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def apply_autonomous(root: str | Path, args: str) -> dict:
    """Parse ``args`` with ``parse_autonomous_command`` and update the live run.

    The run is the Rust ``AutonomousRun`` for this root. It is not a second
    process, and it is not written to the goal sidecar.
    """
    extension = load_extension()
    key = str(Path(root).resolve())
    run = _RUNS.get(key)
    if run is None:
        run = extension.autonomous.AutonomousRun()
        _RUNS[key] = run
    parsed = extension.commands.parse_autonomous(args)
    kind = parsed["command"]
    if kind == "on":
        run.set_enabled(True)
        run.set_limits(parsed["config"])
    elif kind == "off":
        run.set_enabled(False)
    status = run.status()
    return {
        "command": kind,
        "status": status,
        "text": extension.commands.format_autonomous_status(status),
    }


__all__ = ["apply_autonomous", "apply_goal"]
