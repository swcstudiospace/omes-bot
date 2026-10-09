"""Tests for Grok Bot Audit Tracer and Credential Redaction."""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest

import omega_prime
from omega_prime.grokbot.audit import (
    GENESIS_HASH,
    GrokBotAuditTracer,
    default_audit_path,
    main,
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


# -- hash chain ----------------------------------------------------------

JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c"
)
OMK_TOKEN = "omk_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"


def _fill(tracer: GrokBotAuditTracer, count: int) -> None:
    for i in range(count):
        tracer.log_event("tool_call", tool_name=f"tool_{i}", details={"i": i})


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _expected_hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256((record["prev"] + canonical).encode()).hexdigest()


def test_chain_fields_and_genesis(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    first = tracer.log_event("tool_call", tool_name="a", details={"x": 1})
    second = tracer.log_event("tool_call", tool_name="b")

    assert first["seq"] == 1
    assert first["prev"] == GENESIS_HASH
    assert second["seq"] == 2
    assert second["prev"] == first["hash"]
    for record in (first, second):
        assert record["hash"] == _expected_hash(record)
        assert {
            "seq",
            "timestamp",
            "event",
            "tool_name",
            "caller",
            "status",
            "duration_ms",
            "is_error",
            "details",
            "prev",
            "hash",
        } <= set(record)
    stored = [json.loads(line) for line in _lines(tracer.log_path)]
    assert stored == [first, second]
    assert tracer.verify_integrity() == (True, 2, "verified 2 audit records")


def test_missing_log_is_ok_and_creates_nothing(tmp_path: Path):
    target = tmp_path / "nested" / "audit.jsonl"
    tracer = GrokBotAuditTracer(target)
    assert tracer.verify_integrity() == (True, 0, "log does not exist yet")
    assert tracer.read_recent() == []
    assert not target.parent.exists()


def test_details_not_json_serializable_and_default_path(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    record = tracer.log_event("tool_call", details={"path": Path("/tmp/x"), "n": {1}})
    assert record["details"]["path"] == "/tmp/x"
    assert tracer.verify_integrity()[0] is True
    assert (
        default_audit_path(tmp_path) == tmp_path / ".planning" / "grokbot_audit.jsonl"
    )


def test_modified_middle_record_is_detected(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    _fill(tracer, 4)
    lines = _lines(tracer.log_path)
    record = json.loads(lines[1])
    record["status"] = "tampered"
    lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    tracer.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, count, message = tracer.verify_integrity()
    assert ok is False
    assert count == 1
    assert message == "line 2: hash mismatch (record modified)"


def test_invalid_json_and_legacy_lines_are_reported(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    _fill(tracer, 2)
    with open(tracer.log_path, "a", encoding="utf-8") as handle:
        handle.write("{not json}\n")
    assert tracer.verify_integrity() == (False, 2, "line 3: invalid JSON")

    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text('{"event":"tool_call"}\n', encoding="utf-8")
    ok, _count, message = GrokBotAuditTracer(legacy).verify_integrity()
    assert (ok, message) == (False, "line 1: missing hash")


def test_deleted_middle_line_is_detected(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    _fill(tracer, 4)
    lines = _lines(tracer.log_path)
    del lines[1]
    tracer.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, count, message = tracer.verify_integrity()
    assert ok is False
    assert count == 1
    assert message == "line 2: prev mismatch (record removed or reordered)"


def test_swapped_lines_are_detected(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    _fill(tracer, 4)
    lines = _lines(tracer.log_path)
    lines[1], lines[2] = lines[2], lines[1]
    tracer.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, _count, message = tracer.verify_integrity()
    assert ok is False
    assert message == "line 2: prev mismatch (record removed or reordered)"


def test_rotation_keeps_chain_and_prunes_backups(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log, max_bytes=1, backups=2)
    _fill(tracer, 6)

    assert log.is_file()
    assert (tmp_path / "audit.jsonl.1").is_file()
    assert (tmp_path / "audit.jsonl.2").is_file()
    assert not (tmp_path / "audit.jsonl.3").exists()

    assert tracer.verify_integrity() == (True, 1, "verified 1 audit records")
    ok, count, message = tracer.verify_integrity(include_rotated=True)
    assert (ok, count) == (True, 3), message

    active = json.loads(_lines(log)[0])
    rotated = json.loads(_lines(tmp_path / "audit.jsonl.1")[0])
    assert active["seq"] == 6
    assert active["prev"] == rotated["hash"]
    assert rotated["seq"] == 5

    # A new tracer after rotation keeps extending the same chain.
    again = GrokBotAuditTracer(log, max_bytes=1, backups=2)
    assert again.log_event("tool_call")["seq"] == 7
    assert again.verify_integrity(include_rotated=True)[0] is True


def test_rotated_file_tamper_is_detected_with_file_name(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log, max_bytes=1, backups=3)
    _fill(tracer, 4)
    backup = tmp_path / "audit.jsonl.2"
    record = json.loads(_lines(backup)[0])
    record["caller"] = "mallory"
    backup.write_text(json.dumps(record) + "\n", encoding="utf-8")

    ok, _count, message = tracer.verify_integrity(include_rotated=True)
    assert ok is False
    assert message == "line 1: hash mismatch (record modified) [audit.jsonl.2]"
    assert tracer.verify_integrity()[0] is True


def test_rotation_with_zero_backups_drops_old_records(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log, max_bytes=1, backups=0)
    _fill(tracer, 3)
    assert not (tmp_path / "audit.jsonl.1").exists()
    record = json.loads(_lines(log)[0])
    assert record["seq"] == 3
    assert tracer.verify_integrity()[0] is True


def test_files_are_private(tmp_path: Path):
    log = tmp_path / "newdir" / "audit.jsonl"
    tracer = GrokBotAuditTracer(log, max_bytes=1, backups=1)
    _fill(tracer, 3)
    assert stat.S_IMODE(log.parent.stat().st_mode) == 0o700
    for path in (log, tmp_path / "newdir" / "audit.jsonl.1"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("shared", [True, False])
def test_concurrent_threads_share_one_chain(tmp_path: Path, shared: bool):
    log = tmp_path / "audit.jsonl"
    common = GrokBotAuditTracer(log)
    threads_n, per_thread = 8, 15
    errors: list[BaseException] = []

    def work(worker: int) -> None:
        tracer = common if shared else GrokBotAuditTracer(log)
        try:
            for i in range(per_thread):
                tracer.log_event("tool_call", tool_name=f"w{worker}", details={"i": i})
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(threads_n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    total = threads_n * per_thread
    records = [json.loads(line) for line in _lines(log)]
    assert len(records) == total
    assert [r["seq"] for r in records] == list(range(1, total + 1))
    assert len({r["seq"] for r in records}) == total
    assert common.verify_integrity() == (True, total, f"verified {total} audit records")


def test_two_instances_continue_one_chain(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    first = GrokBotAuditTracer(log)
    second = GrokBotAuditTracer(log)
    a = first.log_event("tool_call", tool_name="a")
    b = second.log_event("tool_call", tool_name="b")
    c = first.log_event("tool_call", tool_name="c")
    assert [a["seq"], b["seq"], c["seq"]] == [1, 2, 3]
    assert b["prev"] == a["hash"]
    assert c["prev"] == b["hash"]
    assert second.verify_integrity()[0] is True


def test_torn_tail_is_quarantined_and_chain_resets(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log)
    _fill(tracer, 2)
    last_valid = json.loads(_lines(log)[-1])
    with open(log, "ab") as handle:
        handle.write(b'{"seq":3,"timestamp":"2026-10-')  # crash mid-write

    ok, count, message = tracer.verify_integrity()
    assert (ok, count) == (False, 2)
    assert message.startswith("line 3:")
    assert [r["seq"] for r in tracer.read_recent(10)] == [1, 2]

    stored = tracer.log_event("tool_call", tool_name="after")

    quarantined = sorted(tmp_path.glob("audit.jsonl.corrupt-*"))
    assert len(quarantined) == 1
    assert re.search(r"\.corrupt-\d{8}T\d{6}Z$", quarantined[0].name)
    assert b'"seq":3' in quarantined[0].read_bytes()
    reset, after = (json.loads(line) for line in _lines(log))
    assert reset["event"] == "audit_chain_reset"
    assert reset["prev"] == last_valid["hash"]
    assert reset["seq"] == last_valid["seq"] + 1
    assert reset["details"]["quarantined"] == quarantined[0].name
    assert reset["details"]["reason"]
    assert after == stored
    assert after["prev"] == reset["hash"]
    assert tracer.verify_integrity() == (True, 2, "verified 2 audit records")


def test_corrupt_tail_without_valid_records_restarts_at_genesis(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    log.write_text("garbage\n", encoding="utf-8")
    tracer = GrokBotAuditTracer(log)
    tracer.log_event("tool_call")
    reset = json.loads(_lines(log)[0])
    assert reset["event"] == "audit_chain_reset"
    assert reset["prev"] == GENESIS_HASH
    assert reset["seq"] == 1
    assert len(list(tmp_path.glob("audit.jsonl.corrupt-*"))) == 1
    assert tracer.verify_integrity()[0] is True


def test_tampered_tail_hash_is_quarantined(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log)
    _fill(tracer, 3)
    lines = _lines(log)
    record = json.loads(lines[-1])
    record["status"] = "forged"
    lines[-1] = json.dumps(record)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tracer.log_event("tool_call")
    reset = json.loads(_lines(log)[0])
    assert reset["event"] == "audit_chain_reset"
    assert reset["prev"] == json.loads(lines[1])["hash"]
    assert len(list(tmp_path.glob("audit.jsonl.corrupt-*"))) == 1


def test_read_recent_tails_large_file(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl", max_bytes=0)
    padding = "x" * 3000  # records larger than one read block
    for i in range(30):
        tracer.log_event("tool_call", tool_name=f"t{i}", details={"pad": padding})
    recent = tracer.read_recent(limit=3)
    assert [r["tool_name"] for r in recent] == ["t27", "t28", "t29"]
    assert tracer.read_recent(limit=0) == []
    assert len(tracer.read_recent(limit=1000)) == 30
    with open(tracer.log_path, "a", encoding="utf-8") as handle:
        handle.write("\n   \nnot json\n")
    assert [r["tool_name"] for r in tracer.read_recent(limit=2)] == ["t28", "t29"]


# -- CLI -----------------------------------------------------------------


def test_cli_verify_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log)
    _fill(tracer, 3)

    assert main(["verify", "--path", str(log)]) == 0
    assert "verified 3 audit records" in capsys.readouterr().out

    lines = _lines(log)
    del lines[1]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["verify", "--path", str(log)]) == 1
    assert "line 2: prev mismatch" in capsys.readouterr().out


def test_cli_verify_all_and_tail(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    log = tmp_path / "audit.jsonl"
    tracer = GrokBotAuditTracer(log, max_bytes=1, backups=3)
    _fill(tracer, 4)

    assert main(["verify", "--path", str(log), "--all"]) == 0
    assert "verified 4 audit records" in capsys.readouterr().out

    assert main(["tail", "--path", str(log), "-n", "1"]) == 0
    printed = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [r["seq"] for r in printed] == [4]


def test_module_entry_point(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    _fill(GrokBotAuditTracer(log), 2)
    package_root = Path(omega_prime.__file__).resolve().parent.parent
    env = {**os.environ, "PYTHONPATH": str(package_root)}
    command = [sys.executable, "-m", "omega_prime.grokbot.audit", "verify"]

    ok = subprocess.run(
        [*command, "--path", str(log)], env=env, capture_output=True, text=True
    )
    assert ok.returncode == 0, ok.stderr

    log.write_text(log.read_text(encoding="utf-8").replace("tool_0", "tool_X"))
    bad = subprocess.run(
        [*command, "--path", str(log)], env=env, capture_output=True, text=True
    )
    assert bad.returncode == 1
    assert "line 1" in bad.stdout


# -- redaction -----------------------------------------------------------


def test_redacts_jwt_omk_and_authorization_header():
    assert redact_sensitive(f"jwt={JWT} end") == "jwt=[REDACTED] end"
    assert redact_sensitive(f"token was {OMK_TOKEN}.") == "token was [REDACTED]."
    assert redact_sensitive("Authorization: Bearer abc.def-ghi") == "[REDACTED]"
    assert redact_sensitive("authorization: Basic dXNlcjpwYXNz") == "[REDACTED]"
    assert redact_sensitive("Cookie: sid=abc123; theme=dark") == "[REDACTED]"
    assert redact_sensitive("plain omk and eyJ words") == "plain omk and eyJ words"


def test_sanitize_payload_extra_keys_and_non_mutation():
    payload = {
        "Authorization": "Basic abc",
        "cookie": "sid=1",
        "bearer": "x",
        "credentials": {"a": 1},
        "arg_keys": ["path"],
        "note": f"see {JWT}",
        "items": ({"omk": OMK_TOKEN},),
    }
    snapshot = json.loads(json.dumps(payload, default=list))
    sanitized = sanitize_payload(payload)
    assert sanitized["Authorization"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["bearer"] == "[REDACTED]"
    assert sanitized["credentials"] == "[REDACTED]"
    assert sanitized["arg_keys"] == ["path"]
    assert JWT not in sanitized["note"]
    assert sanitized["items"] == [{"omk": "[REDACTED]"}]
    assert json.loads(json.dumps(payload, default=list)) == snapshot


def test_non_json_values_are_redacted_after_str_conversion(tmp_path: Path):
    class Carrier:
        def __str__(self) -> str:
            return f"Authorization: Bearer {OMK_TOKEN}"

    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    record = tracer.log_event("tool_call", details={"obj": Carrier()})
    assert record["details"]["obj"] == "[REDACTED]"
    assert OMK_TOKEN not in tracer.log_path.read_text(encoding="utf-8")
    assert tracer.verify_integrity()[0] is True


def test_secrets_never_reach_the_log_file(tmp_path: Path):
    tracer = GrokBotAuditTracer(tmp_path / "audit.jsonl")
    tracer.log_event(
        "tool_call",
        details={
            "header": f"Authorization: Bearer {OMK_TOKEN}",
            "blob": f"x {JWT} y",
            "token_text": OMK_TOKEN,
        },
    )
    raw = tracer.log_path.read_text(encoding="utf-8")
    assert OMK_TOKEN not in raw
    assert JWT not in raw
    assert tracer.verify_integrity()[0] is True
