# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Typed connector over the Prime kernel tools (CONN-01).

Sits between the ``prime_*`` kernel tool handlers in
``omega_prime/tools/prime_runtime.py`` and ``omega_prime/prime_kernel``. Every
request is decoded here (version gate, unknown-field strictness, typed
fields) before the connector imports the pinned runtime, builds the kernel or
touches the filesystem, so a rejected request has no side effect.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omega_prime.prime.errors import PrimeError
from omega_prime.prime.types import (
    check_schema_version,
    optional_str,
    reject_unknown,
    require_payload,
    require_str,
)

SCHEMA_VERSION = 1

_VERSION_FIELD = frozenset({"schema_version"})
_CELL_FIELDS = frozenset({"schema_version", "code"})
_FACTORY_RUN_FIELDS = frozenset({"schema_version", "spec_id", "name"})
_RUN_FIELDS = frozenset({"schema_version", "run_id"})
_FACTORY_GRAPH_FIELDS = frozenset({"schema_version", "ref"})
_BASH_FIELDS = frozenset({"schema_version", "command"})
_SKILL_LIST_FIELDS = _VERSION_FIELD
_CRATES_FIELDS = _VERSION_FIELD
_ARGS_FIELDS = frozenset({"schema_version", "args"})


def _decode(raw: Any, fields: frozenset, *, what: str) -> dict:
    """Version gate, shape check and unknown-field rejection for one payload."""
    payload = require_payload(raw, what=what)
    check_schema_version(payload, SCHEMA_VERSION, what=what)
    reject_unknown(payload, fields, what=what)
    return payload


def _require_text(payload: dict, key: str, *, what: str) -> str:
    """A required string that may be empty (an empty command asks for status)."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise PrimeError("bad_type", f"{what}.{key} must be a string")
    return value


@dataclass(frozen=True)
class CellRequest:
    code: str

    @classmethod
    def from_dict(cls, raw: Any) -> CellRequest:
        payload = _decode(raw, _CELL_FIELDS, what="CellRequest")
        return cls(code=require_str(payload, "code", what="CellRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class FactoryRunRequest:
    spec_id: str
    name: str | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> FactoryRunRequest:
        payload = _decode(raw, _FACTORY_RUN_FIELDS, what="FactoryRunRequest")
        return cls(
            spec_id=require_str(payload, "spec_id", what="FactoryRunRequest"),
            name=optional_str(payload, "name", what="FactoryRunRequest"),
        )

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class RunRequest:
    """One factory run id (status, stop and resume share this request)."""

    run_id: str

    @classmethod
    def from_dict(cls, raw: Any) -> RunRequest:
        payload = _decode(raw, _RUN_FIELDS, what="RunRequest")
        return cls(run_id=require_str(payload, "run_id", what="RunRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class FactoryGraphRequest:
    ref: str | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> FactoryGraphRequest:
        payload = _decode(raw, _FACTORY_GRAPH_FIELDS, what="FactoryGraphRequest")
        return cls(ref=optional_str(payload, "ref", what="FactoryGraphRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class BashRequest:
    command: str

    @classmethod
    def from_dict(cls, raw: Any) -> BashRequest:
        payload = _decode(raw, _BASH_FIELDS, what="BashRequest")
        return cls(command=require_str(payload, "command", what="BashRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class SkillListRequest:
    """Typed gate for prime_skill_list (version + unknown-field strictness)."""

    @classmethod
    def from_dict(cls, raw: Any) -> SkillListRequest:
        _decode(raw, _SKILL_LIST_FIELDS, what="SkillListRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class CratesRequest:
    """Typed gate for prime_crates (version + unknown-field strictness)."""

    @classmethod
    def from_dict(cls, raw: Any) -> CratesRequest:
        _decode(raw, _CRATES_FIELDS, what="CratesRequest")
        return cls()

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class GoalCommandRequest:
    """Text after ``/goal``; empty asks for status."""

    args: str

    @classmethod
    def from_dict(cls, raw: Any) -> GoalCommandRequest:
        payload = _decode(raw, _ARGS_FIELDS, what="GoalCommandRequest")
        return cls(args=_require_text(payload, "args", what="GoalCommandRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


@dataclass(frozen=True)
class AutonomousCommandRequest:
    """Text after ``/autonomous``; empty asks for status."""

    args: str

    @classmethod
    def from_dict(cls, raw: Any) -> AutonomousCommandRequest:
        payload = _decode(raw, _ARGS_FIELDS, what="AutonomousCommandRequest")
        return cls(args=_require_text(payload, "args", what="AutonomousCommandRequest"))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}


class KernelConnector:
    """The typed boundary over the in-process Prime kernel for one root.

    ``kernel_for(base, run_child)`` returns the (cached) cell kernel for the
    root; it is only called once a request has decoded.
    """

    def __init__(
        self,
        base: Path,
        run_child: Any,
        kernel_for: Callable[[Path, Any], Any],
    ) -> None:
        self._base = base
        self._run_child = run_child
        self._kernel_for = kernel_for

    def _kernel(self) -> Any:
        return self._kernel_for(self._base, self._run_child)

    def cell(self, request: CellRequest) -> dict:
        return _run(self._kernel().execute(request.code))

    def factory_run(self, request: FactoryRunRequest) -> dict:
        _enable_factory(self._base)
        from omega_prime.prime_kernel.factory_api import factory_run

        return _run(factory_run(request.spec_id, name=request.name))

    def factory_status(self, request: RunRequest) -> dict:
        from omega_prime.prime_kernel.factory_api import factory_status

        return _run(factory_status(request.run_id))

    def factory_stop(self, request: RunRequest) -> dict:
        from omega_prime.prime_kernel.factory_api import factory_stop

        return _run(factory_stop(request.run_id))

    def factory_resume(self, request: RunRequest) -> dict:
        from omega_prime.prime_kernel.factory_api import factory_resume

        return _run(factory_resume(request.run_id))

    def factory_graph(self, request: FactoryGraphRequest) -> dict:
        from omega_prime.prime_kernel.factory_api import factory_graph

        return factory_graph(request.ref)

    def bash(self, request: BashRequest) -> dict:
        from omega_prime.prime_kernel.bash_api import run_bash

        self._kernel()
        return _run(run_bash(request.command))

    def skill_list(self, request: SkillListRequest) -> dict:
        from omega_prime.prime_kernel.skills import list_skills

        return {"skills": list_skills()}

    def crates(self, request: CratesRequest) -> dict:
        from omega_prime.prime_kernel.native import native_status

        return native_status()

    def goal(self, request: GoalCommandRequest) -> dict:
        from omega_prime.prime_kernel.bound import apply_goal

        return apply_goal(self._base, request.args)

    def autonomous(self, request: AutonomousCommandRequest) -> dict:
        from omega_prime.prime_kernel.bound import apply_autonomous

        return apply_autonomous(self._base, request.args)


def _enable_factory(root: Path) -> None:
    from omega_prime.prime_kernel.factory_api import enable_factory

    agent_dir = root / "prime-agent-dir"
    agent_dir.mkdir(parents=True, exist_ok=True)
    enable_factory(agent_dir)
    os.environ["PRIME_AGENT_CODING_AGENT_DIR"] = str(agent_dir)


def _run(coro: Any) -> Any:
    """Run one kernel coroutine from a synchronous tool handler."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


__all__ = [
    "SCHEMA_VERSION",
    "AutonomousCommandRequest",
    "BashRequest",
    "CellRequest",
    "CratesRequest",
    "FactoryGraphRequest",
    "FactoryRunRequest",
    "GoalCommandRequest",
    "KernelConnector",
    "RunRequest",
    "SkillListRequest",
]
