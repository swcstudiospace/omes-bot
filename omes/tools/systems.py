"""Systems pack: desk systems tools as an Omes registry family.

Ports `services/desk-gateway/src/desk_gateway/tools/systems.py`: SQL index
and event queries behind injected clients, a local TTL cache, Tier-1 LSP
diagnostics through the Omes session machinery, contract proposals as
operator-committed bundles (Omes never pushes), and main-ref design reads
behind an injectable VCS reader. No network in tests.
"""

from __future__ import annotations

import secrets
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from omes.credentials.redact import redact_text
from omes.tools.file_ops import FileWorkspace
from omes.tools.lsp import LspSession
from omes.tools.registry import ToolRegistry
from omes.tools.rpc import RpcConnection

SYS_TOOL_NAMES = (
    "sys_index_query",
    "sys_events_query",
    "sys_cache",
    "sys_lsp_diagnostics",
    "sys_contract_propose",
    "sys_design_artifact_get",
)

TIER1 = {"tsjs": (".ts", ".tsx", ".js", ".jsx"), "python": (".py",), "go": (".go",)}
ARTIFACT_LIMIT = 60000


def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}


class CacheStore:
    """In-memory TTL cache. `ttl_sec <= 0` expires immediately."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.time
        self._entries: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any:
        """One value, or None when missing or expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_sec: float = 3600) -> None:
        """Store one value for `ttl_sec` seconds."""
        self._entries[key] = (value, self._clock() + ttl_sec)

    def delete(self, key: str) -> bool:
        """Drop one key. True when something was stored (even expired)."""
        return self._entries.pop(key, None) is not None


def _default_vcs_show(root: str, ref: str, path: str) -> str | None:
    try:
        run = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if run.returncode != 0:
        return None
    return run.stdout


@dataclass
class SystemsContext:
    """Everything the systems tools need. Clients default to unconfigured."""

    root: str | Path = "."
    timescale: Any = None
    greptime: Any = None
    cache: CacheStore = field(default_factory=CacheStore)
    vcs_show: Any = None
    main_ref: str = "origin/main"
    clock: Callable[[], float] | None = None


class SystemsClient:
    """Desk systems tools bound to one context."""

    def __init__(self, ctx: SystemsContext) -> None:
        self.ctx = ctx

    def index_query(self, sql: str, limit: int = 100) -> dict[str, Any]:
        """Run one index SQL query. Errors return empty rows."""
        _check_sql(sql, limit)
        if self.ctx.timescale is None:
            return {"rows": [], "error": "not_configured: index store is not configured"}
        result = self.ctx.timescale(sql, int(limit))
        if not isinstance(result, dict):
            return {"rows": [], "error": "upstream_error: index store returned no object"}
        if result.get("error"):
            return {"rows": [], **result}
        return result

    def events_query(self, sql: str, limit: int = 100) -> dict[str, Any]:
        """Run one event SQL query. Errors return empty rows."""
        _check_sql(sql, limit)
        if self.ctx.greptime is None:
            return {"rows": [], "error": "not_configured: event store is not configured"}
        result = self.ctx.greptime(sql, int(limit))
        if not isinstance(result, dict):
            return {"rows": [], "error": "upstream_error: event store returned no object"}
        if result.get("error"):
            return {"rows": [], **result}
        return result

    def cache(self, action: str, key: str, value: Any = None, ttl_sec: float = 3600) -> dict[str, Any]:
        """Get, set, or delete one namespaced cache entry."""
        if action not in ("get", "set", "delete"):
            raise ValueError("action must be get, set, or delete")
        if not isinstance(key, str) or key == "":
            raise ValueError("key must be a non-empty string")
        namespaced = f"omes:{key}"
        if action == "get":
            return {"key": key, "value": self.ctx.cache.get(namespaced)}
        if action == "delete":
            return {"key": key, "deleted": self.ctx.cache.delete(namespaced)}
        if value is None:
            raise ValueError("set needs a value")
        if isinstance(value, str) and redact_text(value) != value:
            return _error("secret_refused", "cache values may not contain credentials")
        if isinstance(ttl_sec, bool) or not isinstance(ttl_sec, (int, float)):
            raise ValueError("ttl_sec must be a number of seconds")
        self.ctx.cache.set(namespaced, value, ttl_sec)
        return {"key": key, "ok": True}

    def lsp_diagnostics(self, command: Any, path: str, language: str | None = None,
                        timeout: float = 10) -> dict[str, Any]:
        """Tier-1 diagnostics for one repo-relative file via a spawned server."""
        if not _repo_relative(path):
            return _error("invalid_args", "path must be repo-relative")
        resolved = language or _language_for(path)
        if resolved not in TIER1:
            return _error("language_not_tier1",
                          f"{resolved or 'unknown'} is not a Tier-1 language (tsjs, python, go)")
        if not isinstance(command, list) or not command or any(not isinstance(p, str) or p == "" for p in command):
            return _error("invalid_args", "command must be a non-empty argv list")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            return _error("invalid_args", "timeout must be a positive number of seconds")
        workspace = FileWorkspace(self.ctx.root)
        root_path = workspace.root
        read = workspace.read_file(path)
        if "error" in read:
            return read
        connection = RpcConnection(command, cwd=str(root_path), timeout=timeout)
        session = LspSession(connection)
        try:
            session.start(str(root_path), timeout=timeout)
            uri = session.open_document(str(root_path / read["path"]), resolved, read["content"])
            found = session.diagnostics(uri, timeout=timeout)
        except (TimeoutError, EOFError, ValueError, RuntimeError) as exc:
            return {"error": f"lsp session failed: {exc}"}
        finally:
            try:
                session.shutdown(timeout=timeout)
            except Exception:
                pass
            connection.close()
        return {"path": read["path"], "diagnostics": found}

    def contract_propose(self, surface: str, body: str, version: str, summary: str,
                         breaking: bool, consumers_required: list[str],
                         change_id: str | None = None,
                         migration_note: str | None = None) -> dict[str, Any]:
        """Build a contract-change bundle. Returns it; the operator commits."""
        if not _repo_relative(surface):
            raise ValueError("surface must be a repo-relative path")
        if not isinstance(body, str) or body == "":
            raise ValueError("body must be a non-empty string")
        if redact_text(body) != body:
            return _error("secret_refused", "proposal body contains a credential shape")
        if not isinstance(version, str) or version == "":
            raise ValueError("version must be a non-empty string")
        if not isinstance(summary, str) or summary == "":
            raise ValueError("summary must be a non-empty string")
        if not isinstance(consumers_required, list) or not consumers_required or \
                any(not isinstance(c, str) or c == "" for c in consumers_required):
            raise ValueError("consumers_required must be a non-empty list of strings")
        change = change_id or ("ct-" + secrets.token_hex(3))
        proposal = {
            "change_id": change, "proposed_by": "bot-00-omes", "surface": surface,
            "breaking": bool(breaking), "version": version, "summary": summary,
            "migration_note": migration_note, "consumers_required": list(consumers_required),
            "acknowledgements": [],
        }
        record = _emit_changes_yaml(proposal)
        branch = f"bot-00-omes/contract-{change}"
        files = {surface: body, f"contracts/changes/{change}.yaml": record}
        return {
            "ok": True, "proposal": proposal, "branch": branch,
            "bundle": {
                "branch": branch, "files": files,
                "pr_title": f"contract: {change} ({'breaking' if breaking else 'additive'})",
                "pr_body": (
                    f"## Contract change `{change}`\n\n{summary}\n\n"
                    f"- surface: `{surface}`\n- version: {version}\n- breaking: {breaking}\n"
                    f"- consumers required: {', '.join(consumers_required)}\n\n"
                    "Consumers acknowledge with `sys_contract_ack`. QUALITY merges after G-4."
                ),
            },
            "pushed": False,
            "reason": "Omes never pushes; the operator commits this bundle",
        }

    def design_artifact_get(self, path: str, ref: str | None = None) -> dict[str, Any]:
        """Read one file at a VCS ref (default origin/main). Truncates at 60KB."""
        if not _repo_relative(path):
            return _error("invalid_args", "path must be repo-relative")
        reader = self.ctx.vcs_show or (lambda r, p: _default_vcs_show(str(self.ctx.root), r, p))
        text = reader(ref or self.ctx.main_ref, path)
        if text is None:
            return _error("not_found", f"{path} is not on {ref or self.ctx.main_ref}")
        return {"path": path, "content": text[:ARTIFACT_LIMIT], "truncated": len(text) > ARTIFACT_LIMIT}


def _check_sql(sql: Any, limit: Any) -> None:
    if not isinstance(sql, str) or sql == "":
        raise ValueError("sql must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")


def _repo_relative(path: Any) -> bool:
    if not isinstance(path, str) or path == "":
        return False
    candidate = PurePosixPath(path)
    return not candidate.is_absolute() and ".." not in candidate.parts


def _language_for(path: str) -> str | None:
    for language, exts in TIER1.items():
        if path.endswith(exts):
            return language
    if path.endswith(".rs"):
        return "rust"
    return None


def _emit_changes_yaml(proposal: dict[str, Any]) -> str:
    """Emit the fixed contract-change shape as YAML (no PyYAML in Omes)."""
    lines = []
    for key in ("change_id", "proposed_by", "surface", "version", "summary"):
        lines.append(f"{key}: {_yaml_str(proposal[key])}")
    lines.append(f"breaking: {'true' if proposal['breaking'] else 'false'}")
    note = proposal.get("migration_note")
    lines.append(f"migration_note: {('null' if note is None else _yaml_str(note))}")
    lines.append("consumers_required:")
    for consumer in proposal["consumers_required"]:
        lines.append(f"  - {_yaml_str(consumer)}")
    lines.append("acknowledgements: []")
    return "\n".join(lines) + "\n"


def _yaml_str(value: Any) -> str:
    text = str(value)
    if any(c in text for c in ":#\n\"'") or text != text.strip() or text == "":
        return json_escape(text)
    return text


def json_escape(text: str) -> str:
    """Double-quoted scalar (JSON string rules are valid YAML)."""
    import json as _json

    return _json.dumps(text, ensure_ascii=False)


def register_systems_tools(registry: ToolRegistry, client: SystemsClient) -> list[str]:
    """Register the 6 systems tools. Cache writes and proposals need approval."""

    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    handlers = {
        "sys_index_query": lambda sql, limit=100: _wrap(client.index_query, sql, limit=limit),
        "sys_events_query": lambda sql, limit=100: _wrap(client.events_query, sql, limit=limit),
        "sys_cache": lambda action, key, value=None, ttl_sec=3600: _wrap(
            client.cache, action, key, value=value, ttl_sec=ttl_sec),
        "sys_lsp_diagnostics": lambda command, path, language=None, timeout=10: _wrap(
            client.lsp_diagnostics, command, path, language=language, timeout=timeout),
        "sys_contract_propose": lambda surface, body, version, summary, breaking, consumers_required, change_id=None, migration_note=None: _wrap(
            client.contract_propose, surface, body, version, summary, breaking, consumers_required,
            change_id=change_id, migration_note=migration_note),
        "sys_design_artifact_get": lambda path, ref=None: _wrap(client.design_artifact_get, path, ref=ref),
    }
    if set(handlers) != set(SYS_TOOL_NAMES):
        raise RuntimeError("Systems tool handlers drifted from SYS_TOOL_NAMES")
    for name in SYS_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name],
                          requires_approval=name in ("sys_cache", "sys_contract_propose"))
    return list(SYS_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "sys_index_query": ("Run one index SQL query. Read-only.",
                        _object({"sql": _string("SQL text."), "limit": {"type": "integer"}}, ["sql"])),
    "sys_events_query": ("Run one event SQL query. Read-only.",
                         _object({"sql": _string("SQL text."), "limit": {"type": "integer"}}, ["sql"])),
    "sys_cache": ("Get, set, or delete one cache entry. Requires approval.",
                  _object({"action": _string("get, set, or delete."), "key": _string("Entry key."),
                           "value": {"description": "Value for set."}, "ttl_sec": {"type": "number"}},
                          ["action", "key"])),
    "sys_lsp_diagnostics": ("Tier-1 diagnostics for one file via a spawned server. Read-only.",
                            _object({"command": {"type": "array", "items": {"type": "string"}},
                                     "path": _string("Repo-relative path."),
                                     "language": _string("Override the inferred language."),
                                     "timeout": {"type": "number"}}, ["command", "path"])),
    "sys_contract_propose": ("Build a contract-change bundle for the operator. Requires approval.",
                             _object({"surface": _string("Contract surface path."), "body": _string("Surface body."),
                                      "version": _string("Contract version."), "summary": _string("Change summary."),
                                      "breaking": {"type": "boolean"},
                                      "consumers_required": {"type": "array", "items": {"type": "string"}},
                                      "change_id": _string("Change id (generated when absent)."),
                                      "migration_note": _string("Migration note.")},
                                     ["surface", "body", "version", "summary", "breaking", "consumers_required"])),
    "sys_design_artifact_get": ("Read one file at a VCS ref. Read-only.",
                                _object({"path": _string("Repo-relative path."), "ref": _string("VCS ref.")}, ["path"])),
}


__all__ = ["SYS_TOOL_NAMES", "CacheStore", "SystemsClient", "SystemsContext", "register_systems_tools"]
