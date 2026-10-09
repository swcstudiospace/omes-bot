"""Dynamic Capability and Prompt Synchronizer for Grok Bot.

Ensures the Grok Bot system directives, tool manifests, and enabled capabilities
are perfectly aligned with Omega Prime repository rosters and feature flags.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from omega_prime.config import PRIME_FAMILIES, load_config, prime_enabled
from omega_prime.grokbot.manifest import generate_grokbot_manifest, get_assembled_prompt


@dataclass
class SyncReport:
    in_sync: bool
    num_tools: int
    num_skills: int
    num_routines: int
    active_flags: dict[str, bool]
    prompt_length: int
    diff: str | None = None


def get_active_family_flags() -> dict[str, bool]:
    """Retrieve active prime capability family flags."""
    cfg = load_config()
    return {family: prime_enabled(cfg, family) for family in PRIME_FAMILIES}


def check_prompt_sync(manifest_path: Path | str | None = None) -> SyncReport:
    """Compare generated manifest against stored manifest or report current sync state."""
    active_flags = get_active_family_flags()
    current_manifest = generate_grokbot_manifest()

    num_tools = len(current_manifest.get("mcp_server", {}).get("tools", []))
    num_skills = len(current_manifest.get("bot", {}).get("skills", []))
    num_routines = len(current_manifest.get("bot", {}).get("routines", []))
    prompt_len = len(current_manifest.get("bot", {}).get("instructions", ""))

    diff_str = None
    in_sync = True

    if manifest_path:
        p = Path(manifest_path)
        if p.is_file():
            existing = json.loads(p.read_text(encoding="utf-8"))
            existing_str = json.dumps(existing, indent=2, sort_keys=True)
            current_str = json.dumps(current_manifest, indent=2, sort_keys=True)
            if existing_str != current_str:
                in_sync = False
                diff_str = "\n".join(
                    difflib.unified_diff(
                        existing_str.splitlines(),
                        current_str.splitlines(),
                        fromfile=str(p),
                        tofile="generated_manifest",
                        lineterm="",
                    )
                )

    return SyncReport(
        in_sync=in_sync,
        num_tools=num_tools,
        num_skills=num_skills,
        num_routines=num_routines,
        active_flags=active_flags,
        prompt_length=prompt_len,
        diff=diff_str,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize and verify Grok Bot instructions and tools"
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
    args = parser.parse_args()

    report = check_prompt_sync(args.check)

    if args.export_prompt:
        out = Path(args.export_prompt)
        prompt_text = get_assembled_prompt()
        out.write_text(prompt_text, encoding="utf-8")
        print(f"Exported {len(prompt_text)} chars of prompt to {out}")
        return

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
                },
                indent=2,
            )
        )
    else:
        print(
            f"Grok Bot Sync Status: {'IN SYNC' if report.in_sync else 'DRIFT DETECTED'}"
        )
        print(f"  Tools: {report.num_tools}")
        print(f"  Skills: {report.num_skills}")
        print(f"  Routines: {report.num_routines}")
        print(f"  Prompt size: {report.prompt_length} characters")
        print(f"  Active flags: {report.active_flags}")
        if report.diff:
            print("\nDrift diff:\n" + report.diff)

    if not report.in_sync:
        sys.exit(1)


if __name__ == "__main__":
    main()
