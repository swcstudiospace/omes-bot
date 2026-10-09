# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Grok Bot 1-Click Manifest Generator.

Produces a self-contained manifest describing exactly what the Omega Prime tool
host serves, for direct import into Grok Bot settings. The tool list, the
approval-gated list and the capability flags come from the same runtime the host
builds (`load_runtime`), never from a static copy. The manifest never holds a
secret: a supplied token only decides `auth.type`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from omega_prime import __version__ as PACKAGE_VERSION
from omega_prime.config import PRIME_FAMILIES, load_config, prime_enabled
from omega_prime.grokbot._io import atomic_write_text
from omega_prime.mcp_server import (
    SERVER_VERSION,
    Runtime,
    RuntimeConfigError,
    load_runtime,
)

MANIFEST_VERSION = "1.0.0"
DEFAULT_URL = "http://127.0.0.1:8000/sse"
DEFAULT_TOKEN_ENV = "MCP_AUTH_TOKEN"
WILDCARD_HOSTS = frozenset({"0.0.0.0", "::", ""})
WILDCARD_URL_NOTE = (
    "wildcard bind rewritten to loopback; pass --public-url for remote clients"
)
STDIO_COMMAND = ".venv/bin/python -m omega_prime.mcp_server --root ."

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_TRUTHY = ("1", "true", "yes", "on")


def find_repo_root() -> Path:
    """Find repository root relative to this file."""
    return Path(__file__).resolve().parents[2]


def parse_template_sections(template_path: Path) -> dict[str, Any]:
    """Parse sections from OMEGA_PRIME.md template."""
    content = template_path.read_text(encoding="utf-8")
    sections: dict[str, Any] = {}
    current_section = "header"
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
                current_lines = []
            current_section = line[3:].strip().lower()
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    skills = []
    if "enabled skills" in sections:
        for sline in sections["enabled skills"].splitlines():
            s = sline.strip()
            if s.startswith("- "):
                skills.append(s[2:].strip())

    routines = []
    if "routines" in sections:
        for rline in sections["routines"].splitlines():
            r = rline.strip()
            if r.startswith("- "):
                routines.append(r[2:].strip())

    return {
        "name": sections.get("name", "Omega Prime"),
        "description": sections.get("description", ""),
        "skills": skills,
        "routines": routines,
    }


def get_assembled_prompt(root: Path | None = None) -> str:
    """Read the assembled OMEGA_PRIME prompt XML."""
    repo = root or find_repo_root()
    prompt_path = repo / "omega_prime" / "prompts-assembled" / "OMEGA_PRIME.xml"
    if prompt_path.is_file():
        return prompt_path.read_text(encoding="utf-8")
    return ""


def _template_path(repo: Path) -> Path:
    return repo / "omega_prime" / "grokbot" / "templates" / "OMEGA_PRIME.md"


def _read_template(repo: Path) -> dict[str, Any]:
    path = _template_path(repo)
    if path.is_file():
        return parse_template_sections(path)
    return {"name": "Omega Prime", "description": "", "skills": [], "routines": []}


# --- template lint ---------------------------------------------------------


@dataclass(frozen=True)
class TemplateLint:
    """Template entries that name a skill or routine with no file behind it."""

    missing_skills: list[str] = field(default_factory=list)
    missing_routines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_skills and not self.missing_routines


def _entry_name(line: str) -> str:
    """The name of a list entry: the text before the first ` — `."""
    return line.split(" — ", 1)[0].strip()


def lint_template(root: Path | str | None = None) -> TemplateLint:
    """Check every template skill and routine resolves to a file under `root`."""
    repo = Path(root) if root is not None else find_repo_root()
    data = _read_template(repo)
    base = repo / "omega_prime"
    missing_skills: list[str] = []
    for entry in data["skills"]:
        name = _entry_name(entry)
        skill_file = base / "skills" / name / "SKILL.md"
        if not _NAME_RE.match(name) or not skill_file.is_file():
            missing_skills.append(name)
    missing_routines: list[str] = []
    for entry in data["routines"]:
        name = _entry_name(entry)
        routine_file = base / "routines" / f"{name}.md"
        if not _NAME_RE.match(name) or not routine_file.is_file():
            missing_routines.append(name)
    return TemplateLint(missing_skills, missing_routines)


# --- served state ----------------------------------------------------------


def _runtime(
    root: Path, home: Path | str | None, env: Mapping[str, str] | None
) -> Runtime:
    return load_runtime(root, home, env=env)


def served_tools(
    root: Path | str | None = None,
    home: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Names the host serves and the subset that needs approval.

    Raises `RuntimeConfigError` when the host would refuse to start.
    """
    runtime = _runtime(Path(root) if root is not None else find_repo_root(), home, env)
    return list(runtime.tool_names), list(runtime.gated_tools)


def prime_family_flags(
    root: Path | str | None = None, env: Mapping[str, str] | None = None
) -> dict[str, bool]:
    """Which Prime capability families are enabled for `root`.

    Reads `omega-prime.json` and the process environment like the host does;
    an explicit `env` mapping additionally overrides
    `OMEGA_PRIME_PRIME_<FAMILY>_ENABLED`.
    """
    repo = Path(root) if root is not None else find_repo_root()
    config = load_config(repo)
    flags = {family: prime_enabled(config, family) for family in PRIME_FAMILIES}
    if env is not None:
        for family in PRIME_FAMILIES:
            value = env.get(f"OMEGA_PRIME_PRIME_{family.upper()}_ENABLED")
            if value is not None:
                flags[family] = value.strip().lower() in _TRUTHY
    return flags


def _substrate_wired(env: Mapping[str, str] | None) -> bool:
    source = os.environ if env is None else env
    return bool(source.get("SUBSTRATE_URL")) and bool(
        source.get("SUBSTRATE_TOKEN") or source.get("SUBSTRATE_TOKEN_GROK_BOT")
    )


# --- URLs ------------------------------------------------------------------


def _loopback_if_wildcard(url: str) -> tuple[str, bool]:
    """Rewrite a wildcard bind host to 127.0.0.1; report whether it changed."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return url, False
    if (parts.hostname or "") not in WILDCARD_HOSTS:
        return url, False
    try:
        port = parts.port
    except ValueError:
        return url, False
    netloc = "127.0.0.1" if port is None else f"127.0.0.1:{port}"
    return urlunsplit(parts._replace(netloc=netloc)), True


def _endpoints(url: str) -> dict[str, str]:
    parts = urlsplit(url)
    path = parts.path[:-4] if parts.path.endswith("/sse") else ""
    base = urlunsplit((parts.scheme, parts.netloc, path.rstrip("/"), "", ""))
    return {"sse": url, "healthz": f"{base}/healthz", "readyz": f"{base}/readyz"}


# --- manifest --------------------------------------------------------------


def manifest_digest(manifest: Mapping[str, Any]) -> str:
    """sha256 hex of the canonical manifest without its `digest` key."""
    body = {key: value for key, value in manifest.items() if key != "digest"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_manifest(
    root: Path | None = None,
    *,
    host_url: str = DEFAULT_URL,
    transport: str = "sse",
    auth_token: str | None = None,
    public_url: str | None = None,
    home: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    token_env: str | None = DEFAULT_TOKEN_ENV,
    auth_enabled: bool | None = None,
    runtime: Runtime | None = None,
) -> dict[str, Any]:
    """Generate the Grok Bot manifest for what the host at `root` serves.

    `auth_token` only decides `auth.type`; its value is never stored. Pass
    `runtime` to reuse a host's already built `Runtime` instead of loading a
    second registry. Raises `RuntimeConfigError` when the host would refuse
    to start.
    """
    if root is not None:
        repo = Path(root)
    elif runtime is not None:
        repo = runtime.root
    else:
        repo = find_repo_root()
    template_data = _read_template(repo)
    prompt_path = repo / "omega_prime" / "prompts-assembled" / "OMEGA_PRIME.xml"
    system_prompt = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    )

    if runtime is None:
        runtime = _runtime(repo, home, env)
    tools = list(runtime.tool_names)
    flags = prime_family_flags(repo, env)
    lint = lint_template(repo)

    url: str | None = None
    url_note: str | None = None
    endpoints: dict[str, str] = {}
    if transport == "sse":
        url = public_url.rstrip("/") + "/sse" if public_url else host_url
        url, rewritten = _loopback_if_wildcard(url)
        if rewritten:
            url_note = WILDCARD_URL_NOTE
        endpoints = _endpoints(url)

    authenticated = bool(auth_token) if auth_enabled is None else auth_enabled

    mcp_server: dict[str, Any] = {
        "transport": transport,
        "url": url,
        "command": STDIO_COMMAND if transport == "stdio" else None,
        "auth": {
            "type": "bearer" if authenticated else "none",
            "token_env": token_env or None,
            "scopes": ["read", "call"],
        },
        "endpoints": endpoints,
        "rostered_tool_count": len(tools),
        "tools": tools,
        "approval_required": list(runtime.gated_tools),
    }
    if url_note:
        mcp_server["url_note"] = url_note

    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "bot": {
            "name": template_data["name"],
            "version": SERVER_VERSION,
            "package_version": PACKAGE_VERSION,
            "description": template_data["description"],
            "instructions": system_prompt,
            "skills": template_data["skills"],
            "routines": template_data["routines"],
            "integrity": {
                "missing_skills": lint.missing_skills,
                "missing_routines": lint.missing_routines,
                "ok": lint.ok,
            },
        },
        "mcp_server": mcp_server,
        "capabilities": {
            "programming_desk": True,
            "hermes_loop": True,
            "omp_harness": True,
            "prime_agent": any(flags.values()),
            "ultrathink_orchestration": True,
            "substrate_telemetry": _substrate_wired(env),
            "prime_families": flags,
            "transports": ["stdio", "sse"],
        },
    }
    manifest["digest"] = manifest_digest(manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omega-prime-grokbot-manifest")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="MCP server URL for SSE transport",
    )
    parser.add_argument(
        "--public-url",
        default=None,
        help="Public base URL of the server; the manifest URL becomes <it>/sse",
    )
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="MCP transport type",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path for JSON manifest (prints to stdout if omitted)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "Marks the server as bearer-authenticated; the value is never "
            "stored. Prefer --token-env: argv is visible to other users"
        ),
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help="Name of the environment variable that holds the server token",
    )
    args = parser.parse_args(argv)

    if args.token:
        print(
            "warning: --token on the command line is visible to other users; "
            "prefer --token-env",
            file=sys.stderr,
        )
    authenticated = bool(
        args.token or (args.token_env and os.environ.get(args.token_env))
    )

    try:
        manifest = generate_manifest(
            args.root.resolve(),
            host_url=args.url,
            transport=args.transport,
            public_url=args.public_url,
            home=args.home,
            token_env=args.token_env,
            auth_enabled=authenticated,
        )
    except RuntimeConfigError as exc:
        print(f"omega-prime-grokbot-manifest: {exc}", file=sys.stderr)
        return 2

    data = json.dumps(manifest, indent=2)
    if args.out:
        atomic_write_text(args.out, data + "\n", mode=0o644)
        print(f"Manifest written to {args.out}")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())

generate_grokbot_manifest = generate_manifest
