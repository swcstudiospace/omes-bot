# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Decode discipline for the Prime connector layer (CONN-01, CONN-02).

Mirrors Prime's payload decoders (``rlm/__init__.py``
``_spawn_handle_from_payload`` precedent): every field is type-checked,
booleans never pass as ints, unknown fields are rejected, and a payload
declaring a newer ``schema_version`` than the adapter's own is rejected
loudly (the pa-models forward-compat guard made loud, not silent).
"""

from __future__ import annotations

from typing import Any, cast

from omega_prime.prime.errors import PrimeError


def check_schema_version(payload: dict, own_version: int, *, what: str) -> None:
    """Reject a payload from a newer schema than this adapter understands."""
    version = payload.get("schema_version")
    if version is None:
        return
    if isinstance(version, bool) or not isinstance(version, int):
        raise PrimeError("bad_type", f"{what}.schema_version must be int")
    if version > own_version:
        raise PrimeError(
            "unsupported_schema_version",
            f"{what} declares schema_version {version}; this adapter understands <= {own_version}",
        )


def reject_unknown(payload: dict, allowed: frozenset, *, what: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PrimeError(
            "unknown_field", f"{what} got unknown fields: {', '.join(unknown)}"
        )


def require_str(payload: dict, key: str, *, what: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PrimeError("bad_type", f"{what}.{key} must be a non-empty string")
    return value


def optional_str(payload: dict, key: str, *, what: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PrimeError("bad_type", f"{what}.{key} must be a string or null")
    return value


def require_int(payload: dict, key: str, *, what: str, minimum: int = 0) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PrimeError("bad_type", f"{what}.{key} must be int")
    if value < minimum:
        raise PrimeError("bad_value", f"{what}.{key} must be >= {minimum}")
    return value


def optional_int(payload: dict, key: str, *, what: str, minimum: int = 1) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PrimeError("bad_type", f"{what}.{key} must be int or null")
    if value < minimum:
        raise PrimeError("bad_value", f"{what}.{key} must be >= {minimum} or null")
    return value


def require_bool(payload: dict, key: str, *, what: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise PrimeError("bad_type", f"{what}.{key} must be bool")
    return value


def require_member(payload: dict, key: str, members: tuple, *, what: str) -> str:
    value = payload.get(key)
    if value not in members:
        raise PrimeError(
            "bad_value",
            f"{what}.{key} must be one of {', '.join(members)}; got {value!r}",
        )
    return cast(str, value)


def require_payload(raw: Any, *, what: str) -> dict:
    if not isinstance(raw, dict):
        raise PrimeError("bad_type", f"{what} must be a JSON object")
    return raw


__all__ = [
    "check_schema_version",
    "optional_int",
    "optional_str",
    "reject_unknown",
    "require_bool",
    "require_int",
    "require_member",
    "require_payload",
    "require_str",
]
