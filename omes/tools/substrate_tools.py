"""Substrate tool family: product docs plus graph coordination.

``substrate_docs_search`` calls substrate-mcp ``docs_search`` (RAGflow-backed
retrieval) through an injected client. The ``substrate_graph_*`` tools
coordinate desk-pack handoffs through the substrate graph ops with lease
handling. Failures are plain ``{"error": ...}`` results, never exceptions
out of dispatch. The three mutating graph tools require approval.
"""

from __future__ import annotations

from typing import Any

from omes.substrate.client import SubstrateError

SUBSTRATE_TOOL_NAMES = (
    "substrate_docs_search",
    "substrate_graph_claim",
    "substrate_graph_release",
    "substrate_graph_complete",
    "substrate_graph_heartbeat",
)

APPROVALS = {
    "substrate_graph_claim",
    "substrate_graph_release",
    "substrate_graph_complete",
}


def register_substrate_tools(registry: Any, client: Any) -> list[str]:
    """Register every substrate tool. ``client`` is an injected substrate client."""

    def substrate_docs_search_tool(query: str) -> dict:
        return docs_search(client, query)

    def substrate_graph_claim_tool(
        graph_id: str, node_id: str, session_id: str, ttl_seconds: int = 3600
    ) -> dict:
        return graph_claim(client, graph_id, node_id, session_id, ttl_seconds)

    def substrate_graph_release_tool(graph_id: str, node_id: str) -> dict:
        return graph_release(client, graph_id, node_id)

    def substrate_graph_complete_tool(graph_id: str, node_id: str) -> dict:
        return graph_complete(client, graph_id, node_id)

    def substrate_graph_heartbeat_tool(graph_id: str, node_id: str, token: str) -> dict:
        return graph_heartbeat(client, graph_id, node_id, token)

    handlers = {
        "substrate_docs_search": substrate_docs_search_tool,
        "substrate_graph_claim": substrate_graph_claim_tool,
        "substrate_graph_release": substrate_graph_release_tool,
        "substrate_graph_complete": substrate_graph_complete_tool,
        "substrate_graph_heartbeat": substrate_graph_heartbeat_tool,
    }
    if set(handlers) != set(SUBSTRATE_TOOL_NAMES):
        raise RuntimeError("substrate tool handlers drifted from SUBSTRATE_TOOL_NAMES")
    for name in SUBSTRATE_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name, description, parameters, handlers[name], requires_approval=name in APPROVALS
        )
    return list(SUBSTRATE_TOOL_NAMES)


def docs_search(client: Any, query: str) -> dict:
    """Search product docs via the substrate. Failures are ``{"error": ...}``."""
    if not isinstance(query, str) or query == "":
        return {"error": "query must be a non-empty string"}
    try:
        result = client.docs_search(query)
    except SubstrateError as exc:
        return {"error": f"substrate unreachable: {exc}"}
    if not isinstance(result, dict) or not result.get("ok"):
        reason = result.get("error") if isinstance(result, dict) else None
        return {"error": str(reason or "docs plane unconfigured")}
    return {"retrieval": result.get("body")}


def graph_claim(
    client: Any, graph_id: str, node_id: str, session_id: str, ttl_seconds: int = 3600
) -> dict:
    """Claim a graph node for this surface. Returns the lease dict."""
    error = _graph_error(graph_id, node_id)
    if error is not None:
        return error
    if not isinstance(session_id, str) or session_id == "":
        return {"error": "session_id must be a non-empty string"}
    try:
        return client.graph_claim(graph_id, node_id, session_id, ttl_seconds)
    except SubstrateError as exc:
        return {"error": f"substrate unreachable: {exc}"}
    except ValueError as exc:
        return {"error": str(exc)}


def graph_release(client: Any, graph_id: str, node_id: str) -> dict:
    """Release this surface's claim on a node."""
    error = _graph_error(graph_id, node_id)
    if error is not None:
        return error
    try:
        return {"result": client.graph_release(graph_id, node_id)}
    except SubstrateError as exc:
        return {"error": f"substrate unreachable: {exc}"}


def graph_complete(client: Any, graph_id: str, node_id: str) -> dict:
    """Mark a node completed and drop its claim."""
    error = _graph_error(graph_id, node_id)
    if error is not None:
        return error
    try:
        return {"result": client.graph_complete(graph_id, node_id)}
    except SubstrateError as exc:
        return {"error": f"substrate unreachable: {exc}"}


def graph_heartbeat(client: Any, graph_id: str, node_id: str, token: str) -> dict:
    """Refresh the lease TTL for an active claim."""
    error = _graph_error(graph_id, node_id)
    if error is not None:
        return error
    if not isinstance(token, str) or token == "":
        return {"error": "token must be a non-empty lease token"}
    try:
        return client.graph_heartbeat(graph_id, node_id, token)
    except SubstrateError as exc:
        return {"error": f"substrate unreachable: {exc}"}


def _graph_error(graph_id: str, node_id: str) -> dict | None:
    if not isinstance(graph_id, str) or graph_id == "":
        return {"error": "graph_id must be a non-empty string"}
    if not isinstance(node_id, str) or node_id == "":
        return {"error": "node_id must be a non-empty string"}
    return None


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


def _graph_ref(required: list[str], extra: dict | None = None) -> dict:
    properties = {
        "graph_id": _string("Graph ID, e.g. ut-<ts36>-<8hex>."),
        "node_id": _string("Graph-of-Thought node id within the graph."),
    }
    if extra:
        properties.update(extra)
    return {"type": "object", "properties": properties, "required": required}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "substrate_docs_search": (
        "Search the product documentation (RAGflow-backed retrieval through "
        "the substrate). Returns the retrieval payload with citations when a "
        "dataset answers, or an error when the docs plane is unconfigured.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language question for the docs.",
                }
            },
            "required": ["query"],
        },
    ),
    "substrate_graph_claim": (
        "Claim a Graph-of-Thought node for this surface. Returns the lease "
        "(expiry + token) or the existing claim. Requires approval.",
        _graph_ref(
            ["graph_id", "node_id", "session_id"],
            {
                "session_id": _string("This session's id, recorded on the claim."),
                "ttl_seconds": {
                    "type": "integer",
                    "description": "Lease TTL in seconds.",
                    "default": 3600,
                },
            },
        ),
    ),
    "substrate_graph_release": (
        "Release this surface's claim on a node without marking it complete. "
        "Requires approval.",
        _graph_ref(["graph_id", "node_id"]),
    ),
    "substrate_graph_complete": (
        "Mark a node completed and drop its claim. Requires approval.",
        _graph_ref(["graph_id", "node_id"]),
    ),
    "substrate_graph_heartbeat": (
        "Refresh the lease TTL for an active claim using the token from the "
        "claim result.",
        _graph_ref(
            ["graph_id", "node_id", "token"],
            {"token": _string("Lease token from the claim result.")},
        ),
    ),
}

__all__ = [
    "APPROVALS",
    "SUBSTRATE_TOOL_NAMES",
    "docs_search",
    "graph_claim",
    "graph_complete",
    "graph_heartbeat",
    "graph_release",
    "register_substrate_tools",
]
