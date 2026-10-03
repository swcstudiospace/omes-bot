"""Policy advisor: diff a proposed policy change and flag expansions.

The OpenShell advisor shape as a pure function: added tools, added hosts,
and removed read-only entries are widenings that deserve human review.
Narrowing — including narrowing allow-all to an explicit list — is never
an expansion.
"""

from __future__ import annotations

from typing import Any


def diff_policy(old: dict, new: dict) -> dict:
    """Compare two parsed policy dicts. Missing keys tolerate absence."""
    old_tools = _tool_set(old)
    new_tools = _tool_set(new)
    old_hosts = _host_set(old)
    new_hosts = _host_set(new)
    old_readonly = _readonly_set(old)
    new_readonly = _readonly_set(new)

    if old_tools is None or new_tools is None:
        added_tools: list[str] = []
        removed_tools: list[str] = []
    else:
        added_tools = sorted(new_tools - old_tools)
        removed_tools = sorted(old_tools - new_tools)
    added_hosts = sorted(new_hosts - old_hosts)
    removed_hosts = sorted(old_hosts - new_hosts)
    readonly_added = sorted(new_readonly - old_readonly)
    readonly_removed = sorted(old_readonly - new_readonly)

    expansions: list[str] = []
    if old_tools is not None and new_tools is None:
        expansions.append("tools widened to allow-all")
    expansions.extend(f"tool newly allowed: {name}" for name in added_tools)
    expansions.extend(f"host newly allowed: {host}" for host in added_hosts)
    expansions.extend(
        f"read-only protection removed: {glob}" for glob in readonly_removed
    )

    return {
        "added_tools": added_tools,
        "removed_tools": removed_tools,
        "added_hosts": added_hosts,
        "removed_hosts": removed_hosts,
        "readonly_added": readonly_added,
        "readonly_removed": readonly_removed,
        "expansions": expansions,
    }


def _tool_set(policy: dict) -> set[str] | None:
    """The allow set, or None for allow-all (absent allow list)."""
    tools = policy.get("tools") if isinstance(policy, dict) else None
    if not isinstance(tools, dict):
        return None
    allow = tools.get("allow")
    if allow is None:
        return None
    if isinstance(allow, list):
        return {str(name) for name in allow}
    return None


def _host_set(policy: dict) -> set[str]:
    network = policy.get("network") if isinstance(policy, dict) else None
    if not isinstance(network, dict):
        return set()
    hosts = network.get("hosts")
    if not isinstance(hosts, list):
        return set()
    return {str(host).lower() for host in hosts}


def _readonly_set(policy: dict) -> set[str]:
    paths = policy.get("paths") if isinstance(policy, dict) else None
    if not isinstance(paths, dict):
        return set()
    entries = paths.get("read_only")
    if not isinstance(entries, list):
        return set()
    return {str(glob) for glob in entries}


__all__ = ["diff_policy"]
