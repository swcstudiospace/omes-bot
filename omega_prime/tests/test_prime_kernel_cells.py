# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Cells, factory help, and bash against the pinned Prime runtime."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from omega_prime.prime_kernel.bash_api import run_bash
from omega_prime.prime_kernel.cells import PrimeCellKernel
from omega_prime.prime_kernel.checkout import ensure_runtime_imported
from omega_prime.prime_kernel.factory_api import (
    enable_factory,
    factory_help,
    validate_spec,
)
from omega_prime.prime_kernel.host import InProcessHost


def _parent(tmp_path):
    return SimpleNamespace(
        session_dir=tmp_path,
        session_name=None,
        delegate_depth=0,
        max_depth=2,
        max_children=4,
    )


def test_namespace_persists_across_cells(tmp_path):
    runtime = ensure_runtime_imported()
    assert hasattr(runtime.repl, "_compile_cell")
    host = InProcessHost(
        _parent(tmp_path), run_child=lambda prompt, model=None, thinking=None: "pong"
    )
    kernel = PrimeCellKernel(host)
    try:
        first = asyncio.run(kernel.execute("x = 1"))
        second = asyncio.run(kernel.execute("x + 1"))
    finally:
        if getattr(host, "installed", False):
            host.uninstall()
    assert first["ok"] is True
    assert second["ok"] is True
    assert second["value"] == "2"
    assert second["error"] is None


def test_cell_output_is_returned_and_never_written_to_the_process_streams(
    tmp_path, capfd
):
    host = InProcessHost(
        _parent(tmp_path), run_child=lambda prompt, model=None, thinking=None: "pong"
    )
    kernel = PrimeCellKernel(host)
    try:
        printed = asyncio.run(
            kernel.execute(
                "import sys\nprint('to-out')\nprint('to-err', file=sys.stderr)\n6 * 7"
            )
        )
        failed = asyncio.run(kernel.execute("print('before-boom')\n1 / 0"))
    finally:
        if getattr(host, "installed", False):
            host.uninstall()
    seen = capfd.readouterr()
    # A cell's output belongs in its result: the host's own streams are not
    # the bot's (over the MCP tool host, stdout is the wire and stderr its log).
    assert (seen.out, seen.err) == ("", "")
    assert printed["value"] == "42"
    assert printed["stdout"] == "to-out\n"
    assert printed["stderr"] == "to-err\n"
    assert failed["ok"] is False
    assert failed["stdout"] == "before-boom\n"


def test_cell_exit_requests_are_cell_errors_and_the_kernel_keeps_working(tmp_path):
    host = InProcessHost(
        _parent(tmp_path), run_child=lambda prompt, model=None, thinking=None: "pong"
    )
    kernel = PrimeCellKernel(host)
    try:
        exited = asyncio.run(kernel.execute("x = 5\nraise SystemExit(3)"))
        interrupted = asyncio.run(kernel.execute("raise KeyboardInterrupt()"))
        after = asyncio.run(kernel.execute("x + 1"))
    finally:
        if getattr(host, "installed", False):
            host.uninstall()
    assert exited["ok"] is False
    assert exited["error"] == "SystemExit: 3"
    assert interrupted["ok"] is False
    assert interrupted["error"].startswith("KeyboardInterrupt")
    # The namespace survives: the exit request ended the cell, not the kernel.
    assert after["value"] == "6"


def test_cell_spawn_uses_in_process_host(tmp_path):
    host = InProcessHost(
        _parent(tmp_path), run_child=lambda prompt, model=None, thinking=None: "pong"
    )
    kernel = PrimeCellKernel(host)
    try:
        outcome = asyncio.run(
            kernel.execute(
                'await rlm.spawn("hi", name="worker", model="test-provider/test-model")'
            )
        )
    finally:
        if getattr(host, "installed", False):
            host.uninstall()
    assert outcome["ok"] is True
    assert outcome["error"] is None
    assert outcome["value"]


def test_cell_child_answer_visible_only_through_collect(tmp_path):
    host = InProcessHost(
        _parent(tmp_path),
        run_child=lambda prompt, model=None, thinking=None: "cell-secret-answer",
    )
    kernel = PrimeCellKernel(host)
    try:
        spawned = asyncio.run(
            kernel.execute(
                'handle = await rlm.spawn("hi", name="w",'
                ' model="test-provider/test-model")'
            )
        )
        collected = asyncio.run(
            kernel.execute("await rlm.collect(handle, timeout_ms=5000)")
        )
        listed = asyncio.run(kernel.execute("await rlm.list_subagents()"))
    finally:
        if getattr(host, "installed", False):
            host.uninstall()
    assert spawned["ok"] is True
    assert collected["ok"] is True
    assert "cell-secret-answer" in (collected["value"] or "")
    assert listed["ok"] is True
    assert "cell-secret-answer" not in (listed["value"] or "")


def test_factory_help_while_disabled():
    text = factory_help()
    assert isinstance(text, str)
    assert text.strip()


def test_validate_spec_rejects_empty():
    errors = validate_spec(None)
    assert errors
    assert all(isinstance(item, str) and item for item in errors)


def test_enable_factory_keeps_help(tmp_path, monkeypatch):
    enable_factory(tmp_path)
    monkeypatch.setenv("PRIME_AGENT_CODING_AGENT_DIR", str(tmp_path))
    text = factory_help()
    assert isinstance(text, str)
    assert text.strip()


def test_run_bash_echo():
    outcome = asyncio.run(run_bash("echo prime-kernel"))
    assert outcome["exit_code"] == 0
    assert "prime-kernel" in outcome["stdout"]
