"""Enterprise Grok Bot Preflight Health Doctor.

Diagnoses environment readiness, tool rosters, submodule checkouts, native extensions,
manifest consistency, and SSE server port availability with remediation guidance.
"""

from __future__ import annotations

import argparse
import importlib
import json
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omega_prime.grokbot.manifest import find_repo_root, generate_manifest


@dataclass
class DiagnosticCheck:
    id: str
    category: str
    title: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    remediation: str | None = None


class GrokBotDoctor:
    """Preflight diagnostic engine for Grok Bot integration."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or find_repo_root()

    def run_all_checks(self, check_port: int = 8000) -> list[DiagnosticCheck]:
        checks: list[DiagnosticCheck] = []

        # 1. Python Environment
        py_ver = sys.version_info
        if py_ver >= (3, 11):
            checks.append(
                DiagnosticCheck(
                    id="python_version",
                    category="Runtime",
                    title="Python Version",
                    status="PASS",
                    message=f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} satisfies requirement (>= 3.11)",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    id="python_version",
                    category="Runtime",
                    title="Python Version",
                    status="FAIL",
                    message=f"Python {py_ver.major}.{py_ver.minor} is below recommended >= 3.11",
                    remediation="Upgrade Python to 3.11+ using pyenv or system package manager.",
                )
            )

        # 2. Virtual Environment
        is_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )
        checks.append(
            DiagnosticCheck(
                id="virtual_env",
                category="Runtime",
                title="Virtual Environment",
                status="PASS" if is_venv else "WARN",
                message=f"Executing inside venv ({sys.prefix})"
                if is_venv
                else "Not running in an isolated virtual environment",
                remediation=None
                if is_venv
                else "Run: python3 -m venv .venv && source .venv/bin/activate",
            )
        )

        # 3. Submodule: prime-agent
        submodule_path = self.root / "prime-agent"
        gitmodules_file = self.root / ".gitmodules"
        has_submodule_def = (
            gitmodules_file.is_file()
            and "prime-agent" in gitmodules_file.read_text(encoding="utf-8")
        )
        has_checkout = submodule_path.is_dir() and any(submodule_path.iterdir())
        if has_submodule_def and has_checkout:
            checks.append(
                DiagnosticCheck(
                    id="submodule_prime_agent",
                    category="Repository",
                    title="prime-agent Submodule",
                    status="PASS",
                    message="prime-agent submodule is registered and populated",
                )
            )
        elif has_submodule_def:
            checks.append(
                DiagnosticCheck(
                    id="submodule_prime_agent",
                    category="Repository",
                    title="prime-agent Submodule",
                    status="FAIL",
                    message="prime-agent directory is empty or uninitialized",
                    remediation="Run: git submodule update --init --recursive",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    id="submodule_prime_agent",
                    category="Repository",
                    title="prime-agent Submodule",
                    status="WARN",
                    message="prime-agent is not tracked in .gitmodules",
                    remediation="Run: git submodule add https://github.com/PrimeIntellect-ai/prime-agent.git prime-agent",
                )
            )

        # 4. Assembled Prompts
        assembled_prompt = (
            self.root / "omega_prime" / "prompts-assembled" / "OMEGA_PRIME.xml"
        )
        if assembled_prompt.is_file() and assembled_prompt.stat().st_size > 1000:
            checks.append(
                DiagnosticCheck(
                    id="prompt_assembled",
                    category="Prompts",
                    title="Assembled OMEGA_PRIME Prompt",
                    status="PASS",
                    message=f"OMEGA_PRIME.xml exists ({assembled_prompt.stat().st_size} bytes)",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    id="prompt_assembled",
                    category="Prompts",
                    title="Assembled OMEGA_PRIME Prompt",
                    status="FAIL",
                    message="OMEGA_PRIME.xml is missing or empty",
                    remediation="Run: bash omega_prime/scripts/assemble-prompts.sh",
                )
            )

        # 5. Core MCP & Web Packages
        required_pkgs = ["mcp", "starlette", "uvicorn"]
        missing_pkgs = []
        for pkg in required_pkgs:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing_pkgs.append(pkg)
        if not missing_pkgs:
            checks.append(
                DiagnosticCheck(
                    id="mcp_dependencies",
                    category="Dependencies",
                    title="MCP Server Dependencies",
                    status="PASS",
                    message="mcp, starlette, and uvicorn are available",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    id="mcp_dependencies",
                    category="Dependencies",
                    title="MCP Server Dependencies",
                    status="FAIL",
                    message=f"Missing required packages: {', '.join(missing_pkgs)}",
                    remediation=f"Run: pip install {' '.join(missing_pkgs)}",
                )
            )

        # 6. Grok Bot Manifest Generation
        try:
            manifest = generate_manifest(self.root)
            tool_cnt = len(manifest.get("mcp_server", {}).get("tools", []))
            skill_cnt = len(manifest.get("bot", {}).get("skills", []))
            checks.append(
                DiagnosticCheck(
                    id="manifest_generation",
                    category="GrokBot",
                    title="Manifest Generation",
                    status="PASS",
                    message=f"Valid manifest produced ({tool_cnt} tools, {skill_cnt} skills)",
                )
            )
        except Exception as exc:
            checks.append(
                DiagnosticCheck(
                    id="manifest_generation",
                    category="GrokBot",
                    title="Manifest Generation",
                    status="FAIL",
                    message=f"Failed to generate manifest: {exc}",
                    remediation="Inspect OMEGA_PRIME.md template and contracts/tool-rosters/omega-prime.yaml",
                )
            )

        # 7. Local Port Availability for SSE
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        port_in_use = False
        try:
            sock.bind(("127.0.0.1", check_port))
        except OSError:
            port_in_use = True
        finally:
            sock.close()

        if not port_in_use:
            checks.append(
                DiagnosticCheck(
                    id="port_availability",
                    category="Network",
                    title=f"SSE Port {check_port}",
                    status="PASS",
                    message=f"Port {check_port} is free and ready for MCP SSE listener",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    id="port_availability",
                    category="Network",
                    title=f"SSE Port {check_port}",
                    status="WARN",
                    message=f"Port {check_port} is already in use by another process",
                    remediation=f"Choose a different port with --port or stop the service using port {check_port}.",
                )
            )

        # 8. Audit Log Writeability
        audit_file = self.root / ".planning" / "grokbot_audit.jsonl"
        try:
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write("")
            checks.append(
                DiagnosticCheck(
                    id="audit_writeable",
                    category="Audit",
                    title="Audit Trail Storage",
                    status="PASS",
                    message=f"Audit log path {audit_file} is writeable",
                )
            )
        except Exception as exc:
            checks.append(
                DiagnosticCheck(
                    id="audit_writeable",
                    category="Audit",
                    title="Audit Trail Storage",
                    status="FAIL",
                    message=f"Cannot write to audit log: {exc}",
                    remediation=f"Ensure write permissions on {audit_file.parent}",
                )
            )

        return checks


def run_doctor_checks(root: Path | None = None, port: int = 8000) -> dict[str, Any]:
    """Run all preflight doctor checks and return a summary dictionary."""
    doctor = GrokBotDoctor(root)
    checks = doctor.run_all_checks(check_port=port)
    has_failures = any(c.status == "FAIL" for c in checks)
    return {
        "passed": not has_failures,
        "checks": [
            {
                "id": c.id,
                "name": c.title,
                "category": c.category,
                "status": "ok"
                if c.status == "PASS"
                else ("warn" if c.status == "WARN" else "fail"),
                "message": c.message,
                "fix_hint": c.remediation,
            }
            for c in checks
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preflight Health Doctor for Grok Bot native integration"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Check availability of specific SSE port"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON"
    )
    args = parser.parse_args()

    doctor = GrokBotDoctor()
    checks = doctor.run_all_checks(check_port=args.port)

    has_failures = any(c.status == "FAIL" for c in checks)

    if args.json:
        print(
            json.dumps(
                {
                    "healthy": not has_failures,
                    "checks": [asdict(c) for c in checks],
                },
                indent=2,
            )
        )
    else:
        print("=== Omega Prime Grok Bot Health Doctor ===")
        for c in checks:
            tag = f"[{c.status}]"
            print(f"{tag:<8} {c.category:12} - {c.title}: {c.message}")
            if c.remediation and c.status != "PASS":
                print(f"         Remediation: {c.remediation}")
        print("==========================================")
        if has_failures:
            print(
                "Doctor found preflight issues requiring remediation before deployment."
            )
            sys.exit(1)
        else:
            print("All preflight checks passed! Grok Bot integration is ready.")


if __name__ == "__main__":
    main()
