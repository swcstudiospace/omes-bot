"""The Prime connector layer (CONN-01).

Typed, versioned adapters between the tool surface (registry dispatch →
JSON) and the ported Prime capability modules. Each adapter module carries
its own ``SCHEMA_VERSION``; decoders reject unknown fields, bool/int
confusion, values outside the closed Prime vocabularies, and payloads from
a newer schema. The package-level ``SCHEMA_VERSION`` is the maximum of the
per-adapter versions.
"""

from __future__ import annotations

from omega_prime.prime import autonomous, goals, harness, messaging, rlm
from omega_prime.prime.errors import PrimeError

SCHEMA_VERSION = max(
    rlm.SCHEMA_VERSION,
    harness.SCHEMA_VERSION,
    goals.SCHEMA_VERSION,
    autonomous.SCHEMA_VERSION,
    messaging.SCHEMA_VERSION,
)

__all__ = [
    "SCHEMA_VERSION",
    "PrimeError",
    "autonomous",
    "goals",
    "harness",
    "messaging",
    "rlm",
]
