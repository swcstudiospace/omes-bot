# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Shell entry that awaits the pinned MIT Prime ``rlm.bash`` handle.

This loads ``prime-agent/prime-agent-runtime`` (see VENDOR.md) in place. It
does not copy the runtime or reimplement the shell.
"""

from __future__ import annotations

from typing import Any

from omega_prime.prime_kernel.checkout import ensure_runtime_imported


async def run_bash(command: str) -> dict[str, Any]:
    """Run ``command`` through real ``rlm.bash`` and return ``exit_code`` plus stdout."""
    ensure_runtime_imported()
    from rlm.bash import bash

    result = await bash(command)
    return {"exit_code": result.exit_code, "stdout": result.output}
