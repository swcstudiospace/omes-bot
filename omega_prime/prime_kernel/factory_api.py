# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Factory helpers over the pinned MIT Prime runtime.

This loads ``prime-agent/prime-agent-runtime`` (see VENDOR.md) in place and
calls ``rlm.factory`` (``run_factory``, ``status_factory``, ``stop_factory``,
``resume_factory``, ``graph_factory``, ``validate_factory_spec``, and the
embedded help text). It does not copy the Prime runtime.

``enable_factory`` writes ``factory.enabled`` into ``agent_dir/settings.json``.
It does not set ``PRIME_AGENT_CODING_AGENT_DIR``. The tool layer must export
that variable to ``agent_dir`` before any real factory call: the runtime
resolves the agent directory in ``rlm.harness._agent_dir``, and
``factory_enabled`` reads ``settings.json`` from that directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega_prime.prime_kernel.checkout import ensure_runtime_imported


def _factory():
    ensure_runtime_imported()
    from rlm import factory as factory_mod

    return factory_mod


def enable_factory(agent_dir: Path) -> None:
    """Persist ``{"factory": {"enabled": True}}`` without dropping other keys."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    path = agent_dir / "settings.json"
    document: dict[str, Any] = {}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            document = loaded
    factory = document.get("factory")
    if not isinstance(factory, dict):
        factory = {}
    factory["enabled"] = True
    document["factory"] = factory
    path.write_text(json.dumps(document), encoding="utf-8")


async def factory_run(spec_id: str, name: str | None = None) -> dict[str, Any]:
    return await _factory().run_factory(spec_id, name=name)


async def factory_status(run_id: str) -> dict[str, Any]:
    return await _factory().status_factory(run_id)


async def factory_stop(run_id: str) -> dict[str, Any]:
    return await _factory().stop_factory(run_id)


async def factory_resume(run_id: str) -> dict[str, Any]:
    return await _factory().resume_factory(run_id)


def factory_graph(ref: str | None = None) -> dict[str, Any]:
    return _factory().graph_factory(ref)


def factory_help() -> str:
    """Return the embedded factory guide. Readable while the factory is disabled."""
    runtime = ensure_runtime_imported()
    help_fn = getattr(runtime.rlm.factory, "help", None)
    if callable(help_fn):
        text = help_fn()
        if isinstance(text, str) and text:
            return text
    return _factory().FACTORY_HELP


def validate_spec(spec: Any) -> list[str]:
    return _factory().validate_factory_spec(spec)
