# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Persistent Prime cells executed by the pinned MIT runtime compiler.

This loads ``prime-agent/prime-agent-runtime`` (see VENDOR.md) through
``ensure_runtime_imported`` and runs cells with ``rlm.repl._compile_cell`` and
``rlm.repl._run_codes``. It does not copy the Prime runtime or speak NDJSON.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any

from omega_prime.prime_kernel.checkout import ensure_runtime_imported
from omega_prime.prime_kernel.host import InProcessHost


class PrimeCellKernel:
    """One persistent REPL namespace backed by the real Prime cell compiler."""

    def __init__(self, host: InProcessHost) -> None:
        self.host = host
        self._host_installed = False
        runtime = ensure_runtime_imported()
        self.namespace: dict[str, Any] = {"rlm": runtime}

    def _ensure_host(self) -> None:
        if self._host_installed or getattr(self.host, "installed", False):
            self._host_installed = True
            return
        self.host.install()
        self._host_installed = True

    async def execute(self, code: str) -> dict[str, Any]:
        """Compile and run one cell. ``value`` is ``repr`` of the result, or None.

        ``stdout`` and ``stderr`` return what the cell prints while it runs, so
        the bot sees it instead of the host's own streams. The capture swaps the
        process-global streams: text printed later by a thread the cell started
        is not captured, and text other threads print during the cell is.
        ``SystemExit`` and ``KeyboardInterrupt`` are cell errors, as in Prime's
        own kernel, and never end the host.
        """
        self._ensure_host()
        runtime = ensure_runtime_imported()
        repl = runtime.repl
        out, err = io.StringIO(), io.StringIO()
        try:
            codes, _trailing = repl._compile_cell(code, "<prime-cell>")
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = await repl._run_codes(codes, self.namespace)
        except (Exception, SystemExit, KeyboardInterrupt) as exc:
            return {
                "ok": False,
                "value": None,
                "error": f"{type(exc).__name__}: {exc}",
                "stdout": out.getvalue(),
                "stderr": err.getvalue(),
            }
        return {
            "ok": True,
            "value": None if result is None else repr(result),
            "error": None,
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
        }
