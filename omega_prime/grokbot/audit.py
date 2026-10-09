# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tamper-evident structured audit log for Grok Bot tool calls.

Every record is one `\\n`-terminated JSON line in an append-only JSONL file:

    seq, timestamp, event, tool_name, caller, status, duration_ms, is_error,
    details, prev, hash

`hash = sha256(prev + canonical_json(record without hash))` and `prev` is the
`hash` of the previous record (`"0" * 64` for the very first one), so editing,
removing, or reordering any record breaks the chain and `verify_integrity`
names the first bad line. `details` is credential-redacted before it is hashed.

Appends are serialised by a thread lock plus an exclusive `fcntl.flock` on a
`<log>.lock` sidecar (the log itself is renamed on rotation, so it cannot carry
the lock), which lets several threads and processes continue one chain. The
previous hash is read from the end of the file, never by scanning it.

The active file rotates by size (`audit.jsonl` -> `.1` -> `.2` ... `.backups`,
older files are dropped) and the chain carries across the rotation. Files are
created 0600 and a log directory created by the tracer is 0700. A torn or
corrupt tail (crash mid-write) is renamed to `<name>.corrupt-<UTC>` and kept; a
fresh file starts with an `audit_chain_reset` record chained from the last valid
record, so auditing never stops and the break stays visible.

CLI: `python -m omega_prime.grokbot.audit verify|tail`.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from omega_prime.grokbot._io import PRIVATE_FILE_MODE, ensure_private_dir

_fcntl: ModuleType | None
try:
    import fcntl as _fcntl_module

    _fcntl = _fcntl_module
except ImportError:  # pragma: no cover - non-POSIX platforms
    _fcntl = None

GENESIS_HASH = "0" * 64
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUPS = 5
_READ_BLOCK = 8192
_REDACTED = "[REDACTED]"

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
    # JWT-like header.payload.signature triplets (base64url JSON starts with eyJ)
    re.compile(r"eyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]*"),
    # Tokens minted by omega_prime.grokbot.security.generate_token
    re.compile(r"omk_[A-Za-z0-9_\-]{16,}"),
    # Whole header value for credential-carrying headers
    re.compile(r"\b(?:proxy-)?authorization[\"']?\s*[:=]\s*[^\r\n\"']+", re.IGNORECASE),
    re.compile(r"\b(?:set-)?cookie[\"']?\s*[:=]\s*[^\r\n\"']+", re.IGNORECASE),
]

_SENSITIVE_KEY_PARTS = (
    "key",
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "bearer",
    "credential",
)
# Non-secret field names that merely contain a sensitive substring ("arg_keys"
# lists argument names; it never carries values).
_SAFE_KEYS = frozenset({"arg_keys"})


def redact_sensitive(text: str) -> str:
    """Scrub tokens, API keys, and auth headers from text."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern in _REDACT_PATTERNS:
        result = pattern.sub(_REDACTED, result)
    return result


def _is_sensitive_key(key: Any) -> bool:
    name = str(key).lower()
    return name not in _SAFE_KEYS and any(part in name for part in _SENSITIVE_KEY_PARTS)


def sanitize_payload(obj: Any) -> Any:
    """Recursively sanitize dicts and lists for logging (input is not mutated)."""
    if isinstance(obj, str):
        return redact_sensitive(obj)
    if isinstance(obj, dict):
        return {
            k: (_REDACTED if _is_sensitive_key(k) else sanitize_payload(v))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [sanitize_payload(item) for item in obj]
    return obj


def default_audit_path(root: Path | str) -> Path:
    """Default audit log location for a workspace root."""
    return Path(root) / ".planning" / "grokbot_audit.jsonl"


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_hash(record: dict[str, Any]) -> str:
    """Hash of `record` minus its own `hash`, chained through its `prev`."""
    body = {k: v for k, v in record.items() if k != "hash"}
    prev = body.get("prev")
    material = (prev if isinstance(prev, str) else "") + _canonical_json(body)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _normalise(body: dict[str, Any]) -> dict[str, Any]:
    """Round-trip through JSON so the hashed record equals what a reader parses.

    Applies `default=str` to unserialisable values, coerces keys to strings and
    replaces lone surrogates that could not be written as UTF-8.
    """
    text = json.dumps(body, default=str, ensure_ascii=False)
    text = text.encode("utf-8", "replace").decode("utf-8")
    result: dict[str, Any] = json.loads(text)
    return result


def _jsonable(obj: Any) -> Any:
    """Convert `obj` to plain JSON types (`default=str`) so redaction sees the text.

    Never raises: auditing must not fail because a detail is unserialisable.
    """
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError, RecursionError):
        return {"unserializable_details": redact_sensitive(repr(obj)[:200])}


def _record_problem(record: Any) -> str | None:
    """Self-consistency check of one record (no neighbour needed)."""
    if not isinstance(record, dict):
        return "not a JSON object"
    if not isinstance(record.get("hash"), str):
        return "missing hash"
    seq = record.get("seq")
    if isinstance(seq, bool) or not isinstance(seq, int):
        return "missing or invalid seq"
    if not isinstance(record.get("prev"), str):
        return "missing or invalid prev"
    if _compute_hash(record) != record["hash"]:
        return "hash mismatch"
    return None


def _reverse_segments(path: Path) -> Iterator[bytes]:
    """Yield the `\\n`-separated segments of `path`, last first, in block reads.

    A file ending in a newline yields an empty first segment.
    """
    with open(path, "rb") as handle:
        pos = handle.seek(0, os.SEEK_END)
        buf = b""
        while pos > 0:
            step = min(_READ_BLOCK, pos)
            pos -= step
            handle.seek(pos)
            buf = handle.read(step) + buf
            parts = buf.split(b"\n")
            buf = parts[0]
            yield from reversed(parts[1:])
        yield buf


def _parse(segment: bytes) -> Any:
    try:
        return json.loads(segment.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _last_valid_record(path: Path) -> dict[str, Any] | None:
    """Last self-consistent record in `path`, scanning backwards."""
    try:
        for segment in _reverse_segments(path):
            if segment.strip():
                record = _parse(segment)
                if isinstance(record, dict) and _record_problem(record) is None:
                    return record
    except OSError:
        return None
    return None


def _inspect_tail(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """O(1) look at the end of `path`: (last record, None) or (None, problem)."""
    try:
        if path.stat().st_size == 0:
            return None, None
        with open(path, "rb") as handle:
            handle.seek(-1, os.SEEK_END)
            terminated = handle.read(1) == b"\n"
        last: bytes | None = None
        for segment in _reverse_segments(path):
            if segment.strip():
                last = segment
                break
    except FileNotFoundError:
        return None, None
    if last is None:
        return None, None if terminated else "torn last line (no trailing newline)"
    if not terminated:
        return None, "torn last line (no trailing newline)"
    record = _parse(last)
    if record is None:
        return None, "last line is not valid JSON"
    problem = _record_problem(record)
    if problem is not None:
        return None, f"last record invalid: {problem}"
    return record, None


def _rotated_paths(path: Path) -> list[Path]:
    """Existing rotated backups of `path`, newest (`.1`) first."""
    pattern = re.compile(rf"^{re.escape(path.name)}\.(\d+)$")
    found: list[tuple[int, Path]] = []
    try:
        for entry in path.parent.iterdir():
            match = pattern.match(entry.name)
            if match and entry.is_file():
                found.append((int(match.group(1)), entry))
    except OSError:
        return []
    return [p for _, p in sorted(found)]


class GrokBotAuditTracer:
    """Append-only, hash-chained JSONL auditor for Grok Bot operations."""

    def __init__(
        self,
        log_path: Path | str | None = None,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backups: int = DEFAULT_BACKUPS,
    ) -> None:
        self.log_path = (
            default_audit_path(Path.cwd()) if log_path is None else Path(log_path)
        )
        self.max_bytes = max_bytes
        self.backups = max(0, backups)
        self._thread_lock = threading.Lock()

    # -- writing ---------------------------------------------------------

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
        """Append an audit record to the chain and return the stored record."""
        body = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "tool_name": tool_name,
            "caller": caller,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "is_error": is_error,
            "details": sanitize_payload(_jsonable(details or {})),
        }
        with self._locked():
            records: list[dict[str, Any]] = []
            last, problem = _inspect_tail(self.log_path)
            if problem is not None:
                last = self._quarantine(problem, records)
            else:
                self._rotate_if_needed()
                if last is None:
                    last = self._predecessor_record()
            record = self._chain(last, body)
            records.append(record)
            self._append(records)
        return record

    def close(self) -> None:
        """Nothing stays open between records; kept so callers can shut down uniformly."""

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        with self._thread_lock:
            ensure_private_dir(self.log_path.parent)
            lock_path = self.log_path.with_name(self.log_path.name + ".lock")
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
            try:
                if _fcntl is not None:
                    _fcntl.flock(fd, _fcntl.LOCK_EX)
                yield
            finally:
                if _fcntl is not None:
                    with contextlib.suppress(OSError):
                        _fcntl.flock(fd, _fcntl.LOCK_UN)
                os.close(fd)

    @staticmethod
    def _chain(last: dict[str, Any] | None, body: dict[str, Any]) -> dict[str, Any]:
        seq = 1 if last is None else last["seq"] + 1
        prev = GENESIS_HASH if last is None else last["hash"]
        record = _normalise({"seq": seq, **body, "prev": prev})
        record["hash"] = _compute_hash(record)
        return record

    def _append(self, records: list[dict[str, Any]]) -> None:
        data = "".join(_canonical_json(r) + "\n" for r in records).encode("utf-8")
        fd = os.open(
            self.log_path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            PRIVATE_FILE_MODE,
        )
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view) :]
        finally:
            os.close(fd)

    def _backup_path(self, index: int) -> Path:
        return self.log_path.with_name(f"{self.log_path.name}.{index}")

    def _predecessor_record(self) -> dict[str, Any] | None:
        """Last record of the newest rotated file, when the active one is empty."""
        for rotated in _rotated_paths(self.log_path):
            record = _last_valid_record(rotated)
            if record is not None:
                return record
        return None

    def _rotate_if_needed(self) -> None:
        if self.max_bytes <= 0:
            return
        try:
            size = self.log_path.stat().st_size
        except FileNotFoundError:
            return
        if size < self.max_bytes:
            return
        if self.backups == 0:
            self.log_path.unlink()
            return
        with contextlib.suppress(FileNotFoundError):
            self._backup_path(self.backups).unlink()
        for index in range(self.backups - 1, 0, -1):
            with contextlib.suppress(FileNotFoundError):
                os.replace(self._backup_path(index), self._backup_path(index + 1))
        os.replace(self.log_path, self._backup_path(1))

    def _quarantine(
        self, problem: str, records: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Move a corrupt active file aside; queue the reset record; return head."""
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = self.log_path.with_name(f"{self.log_path.name}.corrupt-{stamp}")
        counter = 1
        while target.exists():
            counter += 1
            target = self.log_path.with_name(
                f"{self.log_path.name}.corrupt-{stamp}-{counter}"
            )
        last = _last_valid_record(self.log_path)
        os.replace(self.log_path, target)
        if last is None:
            last = self._predecessor_record()
        reset = self._chain(
            last,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": "audit_chain_reset",
                "tool_name": None,
                "caller": "audit",
                "status": "warning",
                "duration_ms": 0.0,
                "is_error": False,
                "details": {"quarantined": target.name, "reason": problem},
            },
        )
        records.append(reset)
        return reset

    # -- reading ---------------------------------------------------------

    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return up to `limit` newest valid records, oldest first.

        Reads from the end of the file in blocks; blank and unparsable lines are
        skipped.
        """
        if limit <= 0 or not self.log_path.is_file():
            return []
        found: list[dict[str, Any]] = []
        try:
            for segment in _reverse_segments(self.log_path):
                if not segment.strip():
                    continue
                record = _parse(segment)
                if isinstance(record, dict):
                    found.append(record)
                    if len(found) >= limit:
                        break
        except OSError:
            return []
        found.reverse()
        return found

    def verify_integrity(
        self, *, include_rotated: bool = False
    ) -> tuple[bool, int, str]:
        """Verify the hash chain; return `(ok, verified_count, message)`.

        On failure the message is `line N: <reason>` for the first bad line
        (with `[file]` appended when `include_rotated` is set). With
        `include_rotated`, rotated backups are verified oldest to newest as one
        chain together with the active file.
        """
        files: list[Path] = []
        if include_rotated:
            files.extend(reversed(_rotated_paths(self.log_path)))
        if self.log_path.is_file():
            files.append(self.log_path)
        if not files:
            return True, 0, "log does not exist yet"

        count = 0
        prev_hash: str | None = None
        prev_seq: int | None = None
        for file in files:
            suffix = f" [{file.name}]" if include_rotated else ""
            try:
                with open(file, "rb") as handle:
                    for number, raw in enumerate(handle, 1):
                        if not raw.strip():
                            continue
                        record, reason = self._check_line(raw, prev_hash, prev_seq)
                        if record is None:
                            return False, count, f"line {number}: {reason}{suffix}"
                        prev_hash, prev_seq = record["hash"], record["seq"]
                        count += 1
            except OSError as exc:
                return False, count, f"line 0: unreadable ({exc.strerror}){suffix}"
        return True, count, f"verified {count} audit records"

    @staticmethod
    def _check_line(
        raw: bytes, prev_hash: str | None, prev_seq: int | None
    ) -> tuple[dict[str, Any] | None, str]:
        """Validate one line against its predecessor: `(record, "")` or `(None, why)`."""
        record = _parse(raw)
        if record is None:
            return None, "invalid JSON"
        if not isinstance(record, dict):
            return None, "invalid JSON (not an object)"
        if not isinstance(record.get("hash"), str):
            return None, "missing hash"
        if _record_problem(record) is not None:
            return None, "hash mismatch (record modified)"
        # The oldest available record starts the chain; a seq 1 record must be genesis.
        if (prev_hash is not None or record["seq"] == 1) and record["prev"] != (
            GENESIS_HASH if prev_hash is None else prev_hash
        ):
            return None, "prev mismatch (record removed or reordered)"
        if prev_seq is not None and record["seq"] != prev_seq + 1:
            return None, "seq gap"
        if not raw.endswith(b"\n"):
            return None, "torn last line (no trailing newline)"
        return record, ""


# -- CLI -----------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m omega_prime.grokbot.audit",
        description="Inspect the Grok Bot tamper-evident audit log.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    default_hint = "default: $OMEGA_PRIME_AUDIT_LOG or ./.planning/grokbot_audit.jsonl"
    verify = sub.add_parser("verify", help="verify the audit hash chain")
    verify.add_argument("--path", help=f"audit log file ({default_hint})")
    verify.add_argument(
        "--all", action="store_true", help="include rotated backups (.1, .2, ...)"
    )
    tail = sub.add_parser("tail", help="print the newest audit records as JSON lines")
    tail.add_argument("--path", help=f"audit log file ({default_hint})")
    tail.add_argument("-n", type=int, default=20, help="number of records (default 20)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry: `verify` exits 0 when the chain is intact, 1 when broken."""
    args = _build_parser().parse_args(argv)
    path = (
        args.path
        or os.environ.get("OMEGA_PRIME_AUDIT_LOG")
        or default_audit_path(Path.cwd())
    )
    tracer = GrokBotAuditTracer(path)
    if args.command == "verify":
        ok, _count, message = tracer.verify_integrity(include_rotated=args.all)
        print(message)
        return 0 if ok else 1
    for record in tracer.read_recent(args.n):
        print(json.dumps(record, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
