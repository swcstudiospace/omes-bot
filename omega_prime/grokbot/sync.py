# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Dynamic Capability and Prompt Synchronizer for Grok Bot.

Reports drift between a manifest Grok Bot imported and what the host would
export now. Only the content Grok Bot acts on is compared (instructions,
skills, routines, served tools, approval-gated tools, capabilities); where and
how the server is reached (url, command, transport, auth, endpoints) and the
manifest digest never count as drift.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omega_prime.grokbot._io import atomic_write_text
from omega_prime.grokbot.manifest import (
    find_repo_root,
    generate_grokbot_manifest,
    get_assembled_prompt,
    prime_family_flags,
)
from omega_prime.mcp_server import RuntimeConfigError

# Compared sections, as (report name, path inside the manifest).
SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bot.instructions", ("bot", "instructions")),
    ("bot.skills", ("bot", "skills")),
    ("bot.routines", ("bot", "routines")),
    ("mcp_server.tools", ("mcp_server", "tools")),
    ("mcp_server.approval_required", ("mcp_server", "approval_required")),
    ("capabilities", ("capabilities",)),
)


@dataclass
class SyncReport:
    in_sync: bool
    num_tools: int
    num_skills: int
    num_routines: int
    active_flags: dict[str, bool]
    prompt_length: int
    diff: str | None = None
    added_tools: list[str] = field(default_factory=list)
    removed_tools: list[str] = field(default_factory=list)
    changed_sections: list[str] = field(default_factory=list)
    expected_digest: str = ""
    actual_digest: str = ""


def get_active_family_flags(
    root: Path | str | None = None, env: Mapping[str, str] | None = None
) -> dict[str, bool]:
    """Retrieve active prime capability family flags for `root`."""
    return prime_family_flags(root, env)


def _section(manifest: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = manifest
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node


def _semantic(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {name: _section(manifest, path) for name, path in SECTIONS}


def _semantic_digest(semantic: Mapping[str, Any]) -> str:
    text = json.dumps(
        semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(semantic: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    for name, _ in SECTIONS:
        lines.append(f"## {name}")
        value = semantic[name]
        if isinstance(value, str):
            lines.extend(value.splitlines())
        else:
            lines.extend(json.dumps(value, indent=2, sort_keys=True).splitlines())
    return lines


def _names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def check_prompt_sync(
    manifest_path: Path | str | None = None,
    *,
    root: Path | str | None = None,
    home: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> SyncReport:
    """Compare the manifest generated for `root` with a stored manifest file.

    Without `manifest_path` the report only describes the current state. A
    missing file raises `FileNotFoundError`; a file that is not a JSON object
    raises `ValueError`. `root` defaults to the repository containing this
    package, never the working directory.
    """
    repo = Path(root) if root is not None else find_repo_root()
    current = generate_grokbot_manifest(repo, home=home, env=env)
    active_flags = get_active_family_flags(repo, env)

    bot = current.get("bot", {})
    server = current.get("mcp_server", {})
    current_sem = _semantic(current)
    expected_digest = _semantic_digest(current_sem)

    report = SyncReport(
        in_sync=True,
        num_tools=len(server.get("tools", [])),
        num_skills=len(bot.get("skills", [])),
        num_routines=len(bot.get("routines", [])),
        active_flags=active_flags,
        prompt_length=len(bot.get("instructions", "")),
        expected_digest=expected_digest,
        actual_digest=expected_digest,
    )
    if manifest_path is None:
        return report

    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"manifest file not found: {path}")
    existing = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        raise ValueError(f"{path} does not contain a JSON object")

    existing_sem = _semantic(existing)
    report.actual_digest = _semantic_digest(existing_sem)
    report.changed_sections = [
        name for name, _ in SECTIONS if existing_sem[name] != current_sem[name]
    ]
    if not report.changed_sections:
        return report

    report.in_sync = False
    old_tools = set(_names(existing_sem["mcp_server.tools"]))
    new_tools = set(_names(current_sem["mcp_server.tools"]))
    report.added_tools = sorted(new_tools - old_tools)
    report.removed_tools = sorted(old_tools - new_tools)
    report.diff = "\n".join(
        difflib.unified_diff(
            _render(existing_sem),
            _render(current_sem),
            fromfile=str(path),
            tofile="generated_manifest",
            lineterm="",
        )
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omega-prime-grokbot-sync",
        description="Synchronize and verify Grok Bot instructions and tools",
    )
    parser.add_argument(
        "--check",
        type=str,
        default=None,
        help="Check drift against existing manifest file",
    )
    parser.add_argument(
        "--export-prompt",
        type=str,
        default=None,
        help="Export prompt instructions to file",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON status"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: the checkout containing this package)",
    )
    parser.add_argument(
        "--home", type=Path, default=None, help="Home directory for the tool host"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    root = args.root.resolve() if args.root is not None else find_repo_root()
    try:
        report = check_prompt_sync(args.check, root=root, home=args.home)
    except (OSError, ValueError, RuntimeConfigError) as exc:
        print(f"omega-prime-grokbot-sync: {exc}", file=sys.stderr)
        return 2

    if args.export_prompt:
        out = Path(args.export_prompt)
        prompt_text = get_assembled_prompt(root)
        atomic_write_text(out, prompt_text, mode=0o644)
        if not args.json:
            print(f"Exported {len(prompt_text)} chars of prompt to {out}")

    if args.json:
        print(
            json.dumps(
                {
                    "in_sync": report.in_sync,
                    "num_tools": report.num_tools,
                    "num_skills": report.num_skills,
                    "num_routines": report.num_routines,
                    "active_flags": report.active_flags,
                    "prompt_length": report.prompt_length,
                    "has_diff": report.diff is not None,
                    "added_tools": report.added_tools,
                    "removed_tools": report.removed_tools,
                    "changed_sections": report.changed_sections,
                    "expected_digest": report.expected_digest,
                    "actual_digest": report.actual_digest,
                },
                indent=2,
            )
        )
    elif not args.export_prompt or args.check:
        print(
            f"Grok Bot Sync Status: {'IN SYNC' if report.in_sync else 'DRIFT DETECTED'}"
        )
        print(f"  Tools: {report.num_tools}")
        print(f"  Skills: {report.num_skills}")
        print(f"  Routines: {report.num_routines}")
        print(f"  Prompt size: {report.prompt_length} characters")
        print(f"  Active flags: {report.active_flags}")
        if report.changed_sections:
            print(f"  Changed sections: {', '.join(report.changed_sections)}")
        if report.added_tools:
            print(f"  Added tools: {', '.join(report.added_tools)}")
        if report.removed_tools:
            print(f"  Removed tools: {', '.join(report.removed_tools)}")
        if report.diff:
            print("\nDrift diff:\n" + report.diff)

    return 0 if report.in_sync else 1


if __name__ == "__main__":
    sys.exit(main())
