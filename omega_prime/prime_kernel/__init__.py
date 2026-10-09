# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Omega's in-process bridge to the pinned MIT Prime runtime (see VENDOR.md).

Imports the real ``rlm`` package from the Prime checkout. Nothing under
``prime-agent/`` is copied into this tree.
"""

from omega_prime.prime_kernel.checkout import (
    checkout_root,
    ensure_runtime_imported,
    workspace_members,
)
from omega_prime.prime_kernel.host import InProcessHost

__all__ = [
    "InProcessHost",
    "checkout_root",
    "ensure_runtime_imported",
    "workspace_members",
]
