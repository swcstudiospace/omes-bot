"""Enterprise Structured Audit Telemetry for Grok Bot Tool Calls.

Emits append-only JSONL audit events for tool invocations, policy evaluations,
and approvals with automatic credential redaction and rotation support.
"""

from __future__ import annotations

import contextlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Patterns for sensitive credentials to scrub from audit logs
_REDACT_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.~+/]+=*", re.IGNORECASE),
    re.compile(
        r"(?:api_?key|token|secret|password|credential)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.]{8,})[\"']?",
        re.IGNORECASE,
    ),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{36}", re.IGNORECASE),
    re.compile(r"xai-[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
]


def redact_sensitive(text: str) -> str:
    """Scrub tokens, API keys, and auth headers from text."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern in _REDACT_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def sanitize_payload(obj: Any) -> Any:
    """Recursively sanitize dicts and lists for logging."""
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, dict):
        return {
            k: (
                "[REDACTED]"
                if any(s in k.lower() for s in ("key", "token", "secret", "password"))
                else sanitize_payload(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    return obj


class GrokBotAuditTracer:
    """Append-only structured JSONL auditor for Grok Bot operations."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        if log_path is None:
            log_dir = Path.cwd() / ".planning"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_path = log_dir / "grokbot_audit.jsonl"
        else:
            self.log_path = Path(log_path)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event: str,
        *,
        tool_name: str | None = None,
        caller: str = "grok-bot",
        status: str = "ok",
        duration_ms: float = 0.0,
        is_error: bool = False,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an audit event."""
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "tool_name": tool_name,
            "caller": caller,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "is_error": is_error,
            "details": sanitize_payload(details or {}),
        }
        line = json.dumps(payload, separators=(",", ":"))
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return payload

    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read recent audit records."""
        if not self.log_path.is_file():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                with contextlib.suppress(Exception):
                    records.append(json.loads(line))
        return records

    def verify_integrity(self) -> tuple[bool, int, str]:
        """Check that every line in the audit log is valid JSON."""
        if not self.log_path.is_file():
            return True, 0, "log does not exist yet"
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        count = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                count += 1
            except Exception as exc:
                return False, count, f"corrupt JSON on line {i}: {exc}"
        return True, count, f"verified {count} audit records"
