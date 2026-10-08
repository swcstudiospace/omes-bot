"""Seat policy: what one Omega Prime seat may call, write, and reach.

The OpenShell policy shape without kernel drivers: a declarative document
enforced outside the agent's own judgment — at registry dispatch for tools,
at the workspace for writes, and (phase 16) at the transport for network
hosts. The file is JSON so parsing is stdlib-exact. No policy attached
anywhere means today's behavior.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1


class SeatPolicy:
    """Parsed seat policy. Ask ``allows_*``; never branch on raw fields."""

    def __init__(self, document: dict) -> None:
        _check(document)
        self._document = document
        tools = document.get("tools") or {}
        allow = tools.get("allow")
        self._allow_all = allow is None
        self._allowed = frozenset(allow) if isinstance(allow, list) else frozenset()
        paths = document.get("paths") or {}
        self._read_only = tuple(paths.get("read_only") or ())
        network = document.get("network") or {}
        self._hosts = frozenset(host.lower() for host in (network.get("hosts") or ()))

    @classmethod
    def load(cls, path: str | Path) -> SeatPolicy:
        """Parse a policy file. Absent or malformed files raise."""
        target = Path(path)
        if not target.is_file():
            raise FileNotFoundError(f"policy file not found: {target}")
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot parse policy {target}: {exc}") from exc
        if not isinstance(document, dict):
            raise ValueError(f"policy {target} must be a JSON object")
        return cls(document)

    @property
    def seat(self) -> str:
        return str(self._document.get("seat", ""))

    def allows_tool(self, name: str) -> bool:
        """False only when an explicit allow list exists and lacks the name."""
        if self._allow_all:
            return True
        return isinstance(name, str) and name in self._allowed

    def allows_write(self, relative_posix: str) -> bool:
        """False when the jailed relative path matches a read-only glob."""
        if not isinstance(relative_posix, str) or relative_posix == "":
            return False
        candidate = PurePosixPath(relative_posix)
        if candidate.is_absolute() or ".." in candidate.parts:
            return False
        text = candidate.as_posix()
        return not any(_glob_match(glob, text) for glob in self._read_only)

    def allows_host(self, host: str) -> bool:
        """Exact allowlist match, case-insensitive. No implied subdomains."""
        if not isinstance(host, str) or host == "":
            return False
        return host.lower() in self._hosts


def _glob_match(glob: str, text: str) -> bool:
    """Match ``text`` against one glob with ``**`` crossing directories.

    ``pathlib`` trailing-``**`` matching is version-quirky, so this compiles
    the glob explicitly: ``**/`` spans zero or more directories, ``**``
    spans anything, ``*`` and ``?`` stay inside one segment.
    """
    parts: list[str] = []
    index = 0
    while index < len(glob):
        if glob.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif glob.startswith("**", index):
            parts.append(".*")
            index += 2
        elif glob[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif glob[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(glob[index]))
            index += 1
    return re.fullmatch("".join(parts), text) is not None


def _check(document: dict) -> None:
    if document.get("version") != SCHEMA_VERSION:
        raise ValueError(f"policy version must be {SCHEMA_VERSION}")
    tools = document.get("tools", {})
    if not isinstance(tools, dict):
        raise ValueError("policy tools must be an object")
    allow = tools.get("allow")
    if allow is not None and (
        not isinstance(allow, list)
        or any(not isinstance(name, str) or name == "" for name in allow)
    ):
        raise ValueError("policy tools.allow must be a list of names")
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        raise ValueError("policy paths must be an object")
    read_only = paths.get("read_only", [])
    if not isinstance(read_only, list) or any(
        not isinstance(glob, str) or glob == "" for glob in read_only
    ):
        raise ValueError("policy paths.read_only must be a list of globs")
    network = document.get("network", {})
    if not isinstance(network, dict):
        raise ValueError("policy network must be an object")
    hosts = network.get("hosts", [])
    if not isinstance(hosts, list) or any(
        not isinstance(host, str) or host == "" for host in hosts
    ):
        raise ValueError("policy network.hosts must be a list of hosts")


__all__ = ["SCHEMA_VERSION", "SeatPolicy"]
