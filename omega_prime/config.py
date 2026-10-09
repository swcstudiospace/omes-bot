# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Minimal Omega Prime configuration surface.

v10 introduces per-family Prime capability flags. There is intentionally no
central settings module elsewhere in the repo (per-subsystem JSON documents
loaded from explicit paths are the convention — see ``policy/policy.py``
``SeatPolicy.load``); this module is the one small exception, carrying only
the Prime capability gates.

Sources, in precedence order (later wins):

1. Built-in defaults — every Prime family disabled.
2. An optional ``omega-prime.json`` at the repository root (stdlib json, the
   ``SeatPolicy.load`` precedent). Missing file ⇒ defaults.
3. ``OMEGA_PRIME_*`` environment overrides, e.g.
   ``OMEGA_PRIME_PRIME_RLM_ENABLED=1`` sets ``prime.rlm.enabled``.

All flags default off: with every family disabled, Omega Prime behaves
exactly as it did pre-v10 (LOOP-07).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Prime capability families gated by config. Each maps to one rostered tool
# family or loop hook; a disabled family is not registered and is absent from
# the prompt (LOOP-05).
PRIME_FAMILIES: tuple[str, ...] = (
    "rlm",
    "harness",
    "goals",
    "heartbeat",
    "autonomous",
    "messaging",
    "kernel",
)

_ENV_PREFIX = "OMEGA_PRIME_"


def _defaults() -> dict[str, Any]:
    return {"prime": {family: {"enabled": False} for family in PRIME_FAMILIES}}


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``overlay`` onto ``base`` (overlay wins on scalars)."""
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(root: str | Path | None = None) -> dict[str, Any]:
    """Load the merged configuration. A missing config file is not an error."""
    config = _defaults()
    if root is not None:
        path = Path(root) / "omega-prime.json"
        if path.is_file():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("omega-prime.json must contain a JSON object")
            _merge(config, loaded)
    _merge(config, _env_overrides(os.environ))
    return config


def _env_overrides(environ: Mapping[str, str]) -> dict[str, Any]:
    """Map ``OMEGA_PRIME_PRIME_<FAMILY>_ENABLED`` style vars onto the tree."""
    overlay: dict[str, Any] = {}
    for key, value in environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        parts = key[len(_ENV_PREFIX) :].lower().split("_")
        if not parts or parts[0] != "prime":
            continue
        # prime_<family>_enabled — family names are single words today.
        if len(parts) == 3 and parts[1] in PRIME_FAMILIES and parts[2] == "enabled":
            enabled = value.strip().lower() in ("1", "true", "yes", "on")
            overlay.setdefault("prime", {}).setdefault(parts[1], {})["enabled"] = (
                enabled
            )
    return overlay


def prime_enabled(config: dict[str, Any], family: str) -> bool:
    """Whether one Prime capability family is enabled. Unknown ⇒ False."""
    if family not in PRIME_FAMILIES:
        return False
    node = config.get("prime", {}).get(family, {})
    return bool(isinstance(node, dict) and node.get("enabled") is True)


def family_config(config: dict[str, Any], family: str) -> dict[str, Any]:
    """The raw config subtree for one family (empty dict when absent)."""
    node = config.get("prime", {}).get(family, {})
    return node if isinstance(node, dict) else {}


__all__ = ["PRIME_FAMILIES", "family_config", "load_config", "prime_enabled"]
