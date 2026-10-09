"""Grok Bot 1-Click Manifest Generator.

Produces a complete, self-contained manifest payload representing the Omega Prime
agent for direct 1-click import into Grok Bot settings or custom GPT configurations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from omega_prime.mcp_server import roster_names


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


def generate_manifest(
    root: Path | None = None,
    *,
    host_url: str = "http://127.0.0.1:8000/sse",
    transport: str = "sse",
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Generate a production Grok Bot manifest dictionary."""
    repo = root or find_repo_root()
    template_path = repo / "omega_prime" / "grokbot" / "templates" / "OMEGA_PRIME.md"
    prompt_path = repo / "omega_prime" / "prompts-assembled" / "OMEGA_PRIME.xml"
    roster_path = (
        repo / "omega_prime" / "contracts" / "tool-rosters" / "omega-prime.yaml"
    )

    template_data = (
        parse_template_sections(template_path)
        if template_path.is_file()
        else {"name": "Omega Prime", "description": "", "skills": [], "routines": []}
    )

    system_prompt = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    )

    tools = (
        roster_names(roster_path.read_text(encoding="utf-8"))
        if roster_path.is_file()
        else []
    )

    manifest: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "bot": {
            "name": template_data["name"],
            "version": "6.0.0",
            "description": template_data["description"],
            "instructions": system_prompt,
            "skills": template_data["skills"],
            "routines": template_data["routines"],
        },
        "mcp_server": {
            "transport": transport,
            "url": host_url if transport == "sse" else None,
            "command": (
                ".venv/bin/python -m omega_prime.mcp_server --root ."
                if transport == "stdio"
                else None
            ),
            "auth": {
                "type": "bearer" if auth_token else "none",
                "token_env": "MCP_AUTH_TOKEN" if auth_token else None,
            },
            "rostered_tool_count": len(tools),
            "tools": tools,
        },
        "capabilities": {
            "programming_desk": True,
            "hermes_loop": True,
            "omp_harness": True,
            "prime_agent": True,
            "ultrathink_orchestration": True,
            "substrate_telemetry": True,
        },
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omega-prime-grokbot-manifest")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/sse",
        help="MCP server URL for SSE transport",
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
        help="Optional bearer auth token for the MCP server",
    )
    args = parser.parse_args(argv)

    manifest = generate_manifest(
        args.root.resolve(),
        host_url=args.url,
        transport=args.transport,
        auth_token=args.token,
    )

    data = json.dumps(manifest, indent=2)
    if args.out:
        args.out.write_text(data, encoding="utf-8")
        print(f"Manifest written to {args.out}")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())

generate_grokbot_manifest = generate_manifest
