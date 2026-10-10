# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Register the durable-status tool.

Cron job runs persist a turn journal beside ``cron/jobs.json``. This tool
reads that journal and counts workflow checkpoints under ``workflows/``.
It does not start a turn. A missing journal is an explicit absent status,
not an error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega_prime.durable.journal import TurnJournal
from omega_prime.prime.types import reject_extra
from omega_prime.tools.registry import ToolRegistry

DURABLE_TOOL_NAMES = ("durable_status",)


def register_durable_surface_tools(
    registry: ToolRegistry, root: str | Path
) -> list[str]:
    """Register ``durable_status`` against ``root``."""
    base = Path(root)

    def durable_status(**extra: Any) -> dict:
        reject_extra(extra, what="durable_status")
        journal_path = base / "cron" / "turns.sqlite"
        workflow_dir = base / "workflows"
        checkpoints = (
            len(list(workflow_dir.glob("*.json"))) if workflow_dir.is_dir() else 0
        )
        if not journal_path.is_file():
            return {
                "journal": "absent",
                "path": str(journal_path),
                "open_runs": 0,
                "entry_count": 0,
                "last_run_id": None,
                "workflow_checkpoints": checkpoints,
            }
        found = TurnJournal(journal_path).status()
        return {
            "journal": "present",
            "path": str(journal_path),
            "open_runs": found["open_runs"],
            "entry_count": found["entry_count"],
            "last_run_id": found["last_run_id"],
            "workflow_checkpoints": checkpoints,
        }

    registry.register(
        "durable_status",
        "Report the cron turn journal and workflow checkpoint count.",
        {"type": "object", "properties": {}, "required": []},
        durable_status,
    )
    return list(DURABLE_TOOL_NAMES)


__all__ = ["DURABLE_TOOL_NAMES", "register_durable_surface_tools"]
