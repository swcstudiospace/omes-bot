# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Locate the pinned MIT Prime checkout and import its runtime in place.

This loads ``prime-agent/prime-agent-runtime`` (see VENDOR.md) by putting that
source tree on ``sys.path``. It does not copy the Prime runtime into Omega.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from types import ModuleType

_RUNTIME: ModuleType | None = None


def checkout_root() -> Path:
    """Return the pinned ``prime-agent/`` checkout beside the ``omega_prime`` package."""
    return Path(__file__).resolve().parents[2] / "prime-agent"


def runtime_src() -> Path:
    """Return ``prime-agent/prime-agent-runtime/src``, the import root for ``rlm``."""
    return checkout_root() / "prime-agent-runtime" / "src"


def ensure_runtime_imported() -> ModuleType:
    """Insert the Prime runtime source on ``sys.path`` once and import real ``rlm``."""
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    src = str(runtime_src())
    if src not in sys.path:
        sys.path.insert(0, src)
    import rlm
    import rlm.bash
    import rlm.factory
    import rlm.harness
    import rlm.repl

    _RUNTIME = rlm
    return rlm


def workspace_members() -> list[str]:
    """Crate names from ``prime-agent/Cargo.toml`` ``members``, in file order."""
    cargo = tomllib.loads((checkout_root() / "Cargo.toml").read_text(encoding="utf-8"))
    return [Path(member).name for member in cargo["workspace"]["members"]]
