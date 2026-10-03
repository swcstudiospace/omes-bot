"""Omes as a substrate surface: brief, events, shared memory, docs, graph ops.

The client speaks substrate-mcp over HTTP (`POST /brief`, `POST /events`,
`GET /healthz`, `POST /mcp`) on the shared stdlib transport. Briefs and
events are fail-open — a substrate outage never blocks a turn — while shared
memory writes are fail-closed: the caller always learns whether the write
landed. Upstream ground truth is `~/src/repos/agent-substrate`
(`packages/mcp-server/src/server.ts`, `mcp.ts`, `types.ts`).
"""

from __future__ import annotations

from omes.substrate.client import (
    EVENT_KINDS,
    MEMORY_KINDS,
    SubstrateClient,
    SubstrateError,
)
from omes.substrate.session import SubstrateSession

__all__ = [
    "EVENT_KINDS",
    "MEMORY_KINDS",
    "SubstrateClient",
    "SubstrateError",
    "SubstrateSession",
]
