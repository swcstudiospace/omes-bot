# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tools that run Prime Agent's pinned runtime inside this process.

The handlers call the real ``rlm`` package from the read-only ``prime-agent``
checkout (factory, bash, cell compiler, skill packages) and, when the native
extension is built, the linked Rust crates. Registration is gated on
``prime.kernel.enabled`` (default off). A disabled family registers nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from omega_prime.prime.kernel import (
    AutonomousCommandRequest,
    BashRequest,
    CellRequest,
    CratesRequest,
    FactoryGraphRequest,
    FactoryRunRequest,
    GoalCommandRequest,
    KernelConnector,
    RunRequest,
    SkillListRequest,
)
from omega_prime.prime.types import reject_extra
from omega_prime.tools.registry import ToolRegistry

# Offered after messaging. The roster and the seat policy list these names.
KERNEL_TOOL_NAMES = (
    "prime_cell",
    "prime_factory_run",
    "prime_factory_status",
    "prime_factory_stop",
    "prime_factory_resume",
    "prime_factory_graph",
    "prime_bash",
    "prime_skill_list",
    "prime_crates",
    "prime_goal",
    "prime_autonomous",
)

_WRITE_TOOLS = frozenset(
    {
        "prime_cell",
        "prime_factory_run",
        "prime_factory_stop",
        "prime_factory_resume",
        "prime_bash",
        "prime_goal",
        "prime_autonomous",
    }
)

_KERNELS: dict[str, Any] = {}


def register_prime_kernel_tools(
    registry: ToolRegistry,
    root: Any,
    *,
    enabled: bool = True,
    run_child: Any = None,
) -> list[str]:
    """Register the kernel family. ``enabled=False`` registers nothing."""
    if not enabled:
        return []

    connector = KernelConnector(Path(root), run_child, _kernel_for)

    # Every handler rejects undeclared keys, then decodes through the typed,
    # versioned request boundary before the connector imports the pinned
    # runtime, builds the kernel, or touches the filesystem. Registry policy
    # and approval already ran. Required parameters default to None so an
    # omitted field reaches the typed decoder.

    def prime_cell(
        code: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_cell")
        request = CellRequest.from_dict(
            {"code": code, "schema_version": schema_version}
        )
        return connector.cell(request)

    def prime_factory_run(
        spec_id: Any = None,
        name: Any = None,
        schema_version: int | None = None,
        **extra: Any,
    ) -> dict:
        reject_extra(extra, what="prime_factory_run")
        request = FactoryRunRequest.from_dict(
            {"spec_id": spec_id, "name": name, "schema_version": schema_version}
        )
        return connector.factory_run(request)

    def prime_factory_status(
        run_id: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_factory_status")
        request = RunRequest.from_dict(
            {"run_id": run_id, "schema_version": schema_version}
        )
        return connector.factory_status(request)

    def prime_factory_stop(
        run_id: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_factory_stop")
        request = RunRequest.from_dict(
            {"run_id": run_id, "schema_version": schema_version}
        )
        return connector.factory_stop(request)

    def prime_factory_resume(
        run_id: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_factory_resume")
        request = RunRequest.from_dict(
            {"run_id": run_id, "schema_version": schema_version}
        )
        return connector.factory_resume(request)

    def prime_factory_graph(
        ref: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_factory_graph")
        request = FactoryGraphRequest.from_dict(
            {"ref": ref, "schema_version": schema_version}
        )
        return connector.factory_graph(request)

    def prime_bash(
        command: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_bash")
        request = BashRequest.from_dict(
            {"command": command, "schema_version": schema_version}
        )
        return connector.bash(request)

    def prime_skill_list(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="prime_skill_list")
        request = SkillListRequest.from_dict({"schema_version": schema_version})
        return connector.skill_list(request)

    def prime_crates(schema_version: int | None = None, **extra: Any) -> dict:
        reject_extra(extra, what="prime_crates")
        request = CratesRequest.from_dict({"schema_version": schema_version})
        return connector.crates(request)

    def prime_goal(
        args: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_goal")
        request = GoalCommandRequest.from_dict(
            {"args": args, "schema_version": schema_version}
        )
        return connector.goal(request)

    def prime_autonomous(
        args: Any = None, schema_version: int | None = None, **extra: Any
    ) -> dict:
        reject_extra(extra, what="prime_autonomous")
        request = AutonomousCommandRequest.from_dict(
            {"args": args, "schema_version": schema_version}
        )
        return connector.autonomous(request)

    handlers: dict[str, Callable[..., Any]] = {
        "prime_cell": prime_cell,
        "prime_factory_run": prime_factory_run,
        "prime_factory_status": prime_factory_status,
        "prime_factory_stop": prime_factory_stop,
        "prime_factory_resume": prime_factory_resume,
        "prime_factory_graph": prime_factory_graph,
        "prime_bash": prime_bash,
        "prime_skill_list": prime_skill_list,
        "prime_crates": prime_crates,
        "prime_goal": prime_goal,
        "prime_autonomous": prime_autonomous,
    }
    if tuple(handlers) != KERNEL_TOOL_NAMES:
        raise RuntimeError("kernel tool handlers drifted from KERNEL_TOOL_NAMES")
    for name in KERNEL_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in _WRITE_TOOLS,
        )
    return list(KERNEL_TOOL_NAMES)


def _kernel_for(root: Path, run_child: Any) -> Any:
    key = str(root.resolve())
    existing = _KERNELS.get(key)
    if existing is not None:
        return existing
    from omega_prime.prime_kernel.cells import PrimeCellKernel
    from omega_prime.prime_kernel.host import InProcessHost

    session_dir = root / "prime-kernel"
    session_dir.mkdir(parents=True, exist_ok=True)
    parent = SimpleNamespace(
        session_dir=session_dir,
        max_children=8,
        max_depth=4,
        delegate_depth=0,
        session_name="omega-prime",
    )
    host = InProcessHost(parent, run_child=run_child, session_dir=session_dir)
    host.install()
    kernel = PrimeCellKernel(host)
    _KERNELS[key] = kernel
    return kernel


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "prime_cell": (
        "Execute one cell in Prime Agent's persistent kernel. "
        "The namespace survives later prime_cell calls. Top-level await uses "
        "the pinned rlm.repl compiler. rlm.spawn and the other rlm calls reach "
        "the in-process host. Returns ok, value (repr of a trailing expression), "
        "error, and the cell's captured stdout and stderr.",
        _object({"code": _string("Python cell source.")}, ["code"]),
    ),
    "prime_factory_run": (
        "Run a Prime factory spec through the pinned rlm.factory executor.",
        _object(
            {
                "spec_id": _string("Harness factory entry id."),
                "name": _string("Optional run name."),
            },
            ["spec_id"],
        ),
    ),
    "prime_factory_status": (
        "Read one Prime factory run from the pinned executor.",
        _object(
            {"run_id": _string("Run id returned by prime_factory_run.")}, ["run_id"]
        ),
    ),
    "prime_factory_stop": (
        "Stop one Prime factory run.",
        _object({"run_id": _string("Run id.")}, ["run_id"]),
    ),
    "prime_factory_resume": (
        "Resume one Prime factory run.",
        _object({"run_id": _string("Run id.")}, ["run_id"]),
    ),
    "prime_factory_graph": (
        "Return the Prime factory graph for a spec, or the authoring help graph.",
        _object({"ref": _string("Optional spec id.")}, []),
    ),
    "prime_bash": (
        "Run a shell command through Prime Agent's rlm.bash, not a reimplementation.",
        _object({"command": _string("Shell command.")}, ["command"]),
    ),
    "prime_skill_list": (
        "List Prime Agent skill packages in the pinned checkout.",
        _object({}, []),
    ),
    "prime_crates": (
        "Report the nine Prime crates. When the native extension is built, "
        "they are linked into this process; otherwise the list is the checkout "
        "workspace and loaded is false.",
        _object({}, []),
    ),
    "prime_goal": (
        "Apply a Prime /goal command in this process. pa-core parses the "
        "arguments and updates the thread goal. The result is Prime's "
        "camelCase GoalState.",
        _object(
            {"args": _string("Text after /goal. Empty asks for status.")},
            ["args"],
        ),
    ),
    "prime_autonomous": (
        "Apply a Prime /autonomous command in this process. pa-core parses "
        "the arguments, updates the live run, and formats the status block.",
        _object(
            {
                "args": _string(
                    "Text after /autonomous, such as 'status' or 'on --max-turns 5'."
                )
            },
            ["args"],
        ),
    ),
}


__all__ = ["KERNEL_TOOL_NAMES", "register_prime_kernel_tools"]
