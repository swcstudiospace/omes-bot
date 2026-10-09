"""Tests for Grok Bot Audit Tracer and Credential Redaction."""

from pathlib import Path

from omega_prime.grokbot.audit import (
    GrokBotAuditTracer,
    redact_sensitive,
    sanitize_payload,
)


def test_redact_sensitive_strings():
    assert "[REDACTED]" in redact_sensitive(
        "Authorization: Bearer my-secret-token-1234567890"
    )
    assert "[REDACTED]" in redact_sensitive("sk-1234567890abcdef1234567890abcdef")
    assert "[REDACTED]" in redact_sensitive("ghp_123456789012345678901234567890123456")
    assert "[REDACTED]" in redact_sensitive("api_key='secret-key-abcdef12345'")
    assert redact_sensitive("harmless text hello world") == "harmless text hello world"


def test_sanitize_payload():
    payload = {
        "user": "developer",
        "api_key": "secret-value",
        "nested": {
            "token": "bearer-token",
            "message": "Authorization: Bearer secret-auth-token-123",
        },
        "items": ["safe", "sk-abcdef1234567890abcdef12345"],
    }
    sanitized = sanitize_payload(payload)
    assert sanitized["user"] == "developer"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert "[REDACTED]" in sanitized["nested"]["message"]
    assert sanitized["items"][0] == "safe"
    assert "[REDACTED]" in sanitized["items"][1]


def test_audit_tracer_log_and_integrity(tmp_path: Path):
    log_file = tmp_path / "test_audit.jsonl"
    tracer = GrokBotAuditTracer(log_file)

    tracer.log_event(
        "tool_call",
        tool_name="read_file",
        caller="grok",
        status="ok",
        duration_ms=12.5,
        details={"path": "omega_prime/config.py", "token": "sensitive12345"},
    )
    tracer.log_event(
        "approval_granted",
        tool_name="run_terminal",
        caller="operator",
        status="ok",
        duration_ms=1.2,
    )

    valid, count, _msg = tracer.verify_integrity()
    assert valid is True
    assert count == 2

    recent = tracer.read_recent(limit=10)
    assert len(recent) == 2
    assert recent[0]["tool_name"] == "read_file"
    assert recent[0]["details"]["token"] == "[REDACTED]"
    assert recent[1]["tool_name"] == "run_terminal"
