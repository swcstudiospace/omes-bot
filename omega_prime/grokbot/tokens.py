# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Scoped, expiring, revocable bearer tokens kept in a hashed JSON file.

File format (`--token-store PATH`)::

    {"version": 1, "tokens": [
        {"id": "tok_1a2b3c4d", "sha256": "<hex>", "scopes": ["read", "call"],
         "label": "ci", "created_at": "2026-01-01T00:00:00Z",
         "expires_at": null, "revoked_at": null}]}

Only the SHA-256 of a token is stored; the plaintext is returned once by
`create_token` and never written anywhere. The file is replaced atomically with mode
0600 under an exclusive `flock` on a sibling `<name>.lock`, so concurrent CLI calls do
not lose each other's updates.

`FileTokenStore` is a `security.TokenStore`, so `AuthMiddleware` uses it unchanged. It
fails closed: a missing, unreadable, corrupt or wrong-version file denies EVERYONE,
sets `degraded` and `degraded_reason` (never file contents), and `enabled` stays True
so a bad file can never mean "no authentication". A later good file clears the state.

CLI: `python -m omega_prime.grokbot.tokens {new,list,revoke}`.
"""

from __future__ import annotations

import argparse
import contextlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from omega_prime.grokbot._io import (
    PRIVATE_FILE_MODE,
    atomic_write_json,
    ensure_private_dir,
)
from omega_prime.grokbot.security import (
    SCOPE_CALL,
    SCOPE_READ,
    SCOPES,
    Principal,
    SecurityConfigError,
    TokenStore,
    generate_token,
    hash_token,
)

_fcntl: ModuleType | None
try:
    import fcntl as _fcntl_module
except ImportError:  # pragma: no cover - non-POSIX platforms
    _fcntl = None
else:
    _fcntl = _fcntl_module

FORMAT_VERSION = 1
TOKEN_ID_PREFIX = "tok_"
DEFAULT_RELOAD_INTERVAL = 1.0
DEFAULT_CLI_SCOPES = (SCOPE_READ, SCOPE_CALL)

STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_REVOKED = "revoked"

_SECONDS_PER_DAY = 86400
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")
_SCOPE_ORDER = {scope: index for index, scope in enumerate(SCOPES)}

Clock = Callable[[], float]


class TokenFileError(ValueError):
    """The token file is unreadable, corrupt, or of an unsupported version."""


def _format_time(epoch: float) -> str:
    return datetime.fromtimestamp(int(epoch), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: str) -> float:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    held = frozenset(scopes)
    if not held:
        raise SecurityConfigError("a token needs at least one scope")
    unknown = sorted(held.difference(SCOPES))
    if unknown:
        raise SecurityConfigError(
            f"unknown token scope(s): {', '.join(unknown)}; "
            f"valid scopes are {', '.join(SCOPES)}"
        )
    return tuple(sorted(held, key=_SCOPE_ORDER.__getitem__))


@dataclass(frozen=True)
class TokenRecord:
    """One stored credential. `sha256` is the digest of the plaintext token."""

    id: str
    sha256: str
    scopes: tuple[str, ...]
    label: str
    created_at: str
    expires_at: str | None = None
    revoked_at: str | None = None

    def status(self, now: float) -> str:
        """`revoked`, `expired` (when `now >= expires_at`) or `active`."""
        if self.revoked_at is not None:
            return STATUS_REVOKED
        if self.expires_at is not None and now >= _parse_time(self.expires_at):
            return STATUS_EXPIRED
        return STATUS_ACTIVE

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sha256": self.sha256,
            "scopes": list(self.scopes),
            "label": self.label,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
        }

    def public_json(self, now: float) -> dict[str, Any]:
        """Listing view: never includes the digest."""
        data = self.to_json()
        del data["sha256"]
        data["status"] = self.status(now)
        return data


def _optional_time(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TokenFileError(f"token record field {key!r} must be a string or null")
    try:
        _parse_time(value)
    except ValueError as exc:
        raise TokenFileError(f"token record field {key!r} is not ISO-8601") from exc
    return value


def _record_from_json(raw: Any) -> TokenRecord:
    if not isinstance(raw, dict):
        raise TokenFileError("token record must be an object")
    token_id = raw.get("id")
    digest = raw.get("sha256")
    scopes = raw.get("scopes")
    label = raw.get("label", "")
    created = raw.get("created_at")
    if not isinstance(token_id, str) or not token_id:
        raise TokenFileError("token record has no id")
    if (
        not isinstance(digest, str)
        or len(digest) != _SHA256_HEX_LENGTH
        or not _HEX_DIGITS.issuperset(digest.lower())
    ):
        raise TokenFileError("token record sha256 is not a SHA-256 hex digest")
    if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
        raise TokenFileError("token record scopes must be a list of strings")
    if not isinstance(label, str):
        raise TokenFileError("token record label must be a string")
    if not isinstance(created, str):
        raise TokenFileError("token record created_at must be a string")
    try:
        normalized = _normalize_scopes(scopes)
    except SecurityConfigError as exc:
        raise TokenFileError("token record has invalid scopes") from exc
    return TokenRecord(
        id=token_id,
        sha256=digest.lower(),
        scopes=normalized,
        label=label,
        created_at=created,
        expires_at=_optional_time(raw, "expires_at"),
        revoked_at=_optional_time(raw, "revoked_at"),
    )


def _parse_file(data: bytes) -> list[TokenRecord]:
    try:
        document = json.loads(data)
    except ValueError as exc:
        raise TokenFileError("token file is not valid JSON") from exc
    if not isinstance(document, dict):
        raise TokenFileError("token file must contain a JSON object")
    if document.get("version") != FORMAT_VERSION:
        raise TokenFileError("unsupported token file version")
    tokens = document.get("tokens")
    if not isinstance(tokens, list):
        raise TokenFileError("token file 'tokens' must be a list")
    return [_record_from_json(item) for item in tokens]


def _read_records(path: Path) -> list[TokenRecord]:
    """Records in `path`; a missing file is an empty store, a bad one raises."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise TokenFileError(f"token file unreadable ({type(exc).__name__})") from exc
    return _parse_file(data)


def _write_records(path: Path, records: Sequence[TokenRecord]) -> None:
    atomic_write_json(
        path,
        {
            "version": FORMAT_VERSION,
            "tokens": [record.to_json() for record in records],
        },
        mode=PRIVATE_FILE_MODE,
    )


@contextlib.contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive `flock` on `<path>.lock` for a read-modify-write cycle."""
    ensure_private_dir(path.parent)
    lock_path = path.with_name(f"{path.name}.lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the lock


def create_token(
    path: Path | str,
    *,
    scopes: Iterable[str],
    label: str = "",
    ttl_days: float | None = None,
    clock: Clock = time.time,
) -> tuple[str, TokenRecord]:
    """Mint a token; returns `(plaintext, record)`. The plaintext is not stored."""
    target = Path(path)
    held = _normalize_scopes(scopes)
    if ttl_days is not None and ttl_days <= 0:
        raise ValueError("ttl_days must be positive")
    plaintext = generate_token()
    now = clock()
    with _exclusive_lock(target):
        records = _read_records(target)
        used = {record.id for record in records}
        token_id = f"{TOKEN_ID_PREFIX}{secrets.token_hex(4)}"
        while token_id in used:
            token_id = f"{TOKEN_ID_PREFIX}{secrets.token_hex(4)}"
        record = TokenRecord(
            id=token_id,
            sha256=hash_token(plaintext),
            scopes=held,
            label=label,
            created_at=_format_time(now),
            expires_at=(
                None
                if ttl_days is None
                else _format_time(now + ttl_days * _SECONDS_PER_DAY)
            ),
        )
        _write_records(target, [*records, record])
    return plaintext, record


def list_tokens(path: Path | str) -> list[TokenRecord]:
    """All stored records (digests only); a missing file lists nothing."""
    return _read_records(Path(path))


def revoke_token(path: Path | str, token_id: str, *, clock: Clock = time.time) -> bool:
    """Revoke `token_id`. Idempotent; False when the id is unknown."""
    target = Path(path)
    with _exclusive_lock(target):
        records = _read_records(target)
        updated: list[TokenRecord] = []
        found = False
        changed = False
        for record in records:
            if record.id == token_id:
                found = True
                if record.revoked_at is None:
                    record = TokenRecord(
                        id=record.id,
                        sha256=record.sha256,
                        scopes=record.scopes,
                        label=record.label,
                        created_at=record.created_at,
                        expires_at=record.expires_at,
                        revoked_at=_format_time(clock()),
                    )
                    changed = True
            updated.append(record)
        if changed:
            _write_records(target, updated)
    return found


@dataclass(frozen=True)
class _Entry:
    principal: Principal
    digest: bytes
    expires_at: float | None
    revoked: bool

    def valid(self, now: float) -> bool:
        if self.revoked:
            return False
        return self.expires_at is None or now < self.expires_at


def _entry_from_record(record: TokenRecord) -> _Entry:
    expires = None if record.expires_at is None else _parse_time(record.expires_at)
    return _Entry(
        principal=Principal(record.id, frozenset(record.scopes), record.label),
        digest=record.sha256.encode("ascii"),
        expires_at=expires,
        revoked=record.revoked_at is not None,
    )


class FileTokenStore(TokenStore):
    """A `TokenStore` backed by the hashed token file; live-reloading, fail closed."""

    def __init__(
        self,
        path: Path | str,
        *,
        clock: Clock = time.time,
        reload_interval: float = DEFAULT_RELOAD_INTERVAL,
    ) -> None:
        super().__init__(())
        self.path = Path(path)
        self._clock = clock
        self._reload_interval = reload_interval
        self._lock = threading.Lock()
        self._file_entries: tuple[_Entry, ...] = ()
        self._signature: tuple[int, int] | None = None
        self._last_check = 0.0
        self._degraded_reason: str | None = None
        with self._lock:
            self._reload()
            self._last_check = self._clock()

    @property
    def enabled(self) -> bool:
        return True

    @property
    def degraded(self) -> bool:
        with self._lock:
            return self._degraded_reason is not None

    @property
    def degraded_reason(self) -> str | None:
        with self._lock:
            return self._degraded_reason

    def _reload(self) -> None:
        """Re-read the file; caller holds `self._lock`."""
        try:
            with self.path.open("rb") as handle:
                info = os.fstat(handle.fileno())
                data = handle.read()
        except FileNotFoundError:
            self._fail("token file not found", None)
            return
        except OSError as exc:
            self._fail(f"token file unreadable ({type(exc).__name__})", None)
            return
        signature = (info.st_mtime_ns, info.st_size)
        try:
            records = _parse_file(data)
        except TokenFileError as exc:
            self._fail(str(exc), signature)
            return
        self._file_entries = tuple(_entry_from_record(record) for record in records)
        self._signature = signature
        self._degraded_reason = None

    def _fail(self, reason: str, signature: tuple[int, int] | None) -> None:
        self._file_entries = ()
        self._signature = signature
        self._degraded_reason = reason

    def _refresh(self) -> tuple[_Entry, ...]:
        with self._lock:
            now = self._clock()
            elapsed = now - self._last_check
            if elapsed >= self._reload_interval or elapsed < 0:
                self._last_check = now
                try:
                    info = self.path.stat()
                except OSError:
                    current: tuple[int, int] | None = None
                else:
                    current = (info.st_mtime_ns, info.st_size)
                if current is None:
                    if self._degraded_reason != "token file not found":
                        self._reload()
                elif current != self._signature:
                    self._reload()
            return self._file_entries

    def verify(self, presented: str | None) -> Principal | None:
        """The principal for a valid, unexpired, unrevoked token; else None.

        Every record is compared with `hmac.compare_digest` (no early exit).
        """
        if not presented:
            return None
        entries = self._refresh()
        digest = hash_token(presented).encode("ascii")
        now = self._clock()
        match: Principal | None = None
        for entry in entries:
            equal = hmac.compare_digest(digest, entry.digest)
            if equal and match is None and entry.valid(now):
                match = entry.principal
        return match

    def principals(self) -> list[Principal]:
        entries = self._refresh()
        now = self._clock()
        return [entry.principal for entry in entries if entry.valid(now)]


class CompositeTokenStore(TokenStore):
    """Several stores behind one: the first match wins, every store is evaluated."""

    def __init__(self, stores: Sequence[TokenStore]) -> None:
        super().__init__(())
        self._stores = tuple(stores)

    @property
    def enabled(self) -> bool:
        return any(store.enabled for store in self._stores)

    @property
    def degraded(self) -> bool:
        return any(getattr(store, "degraded", False) for store in self._stores)

    @property
    def degraded_reason(self) -> str | None:
        for store in self._stores:
            reason = getattr(store, "degraded_reason", None)
            if reason:
                return str(reason)
        return None

    def verify(self, presented: str | None) -> Principal | None:
        match: Principal | None = None
        for store in self._stores:
            principal = store.verify(presented)
            if match is None:
                match = principal
        return match

    def principals(self) -> list[Principal]:
        return [p for store in self._stores for p in store.principals()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m omega_prime.grokbot.tokens",
        description="Manage the hashed Grok Bot token file.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="mint a token (plaintext is printed once)")
    new.add_argument("--file", required=True, help="token file path")
    new.add_argument(
        "--scope",
        action="append",
        dest="scopes",
        help=f"scope to grant ({', '.join(SCOPES)}); repeatable; "
        f"default: {', '.join(DEFAULT_CLI_SCOPES)}",
    )
    new.add_argument("--label", default="", help="free-form label")
    new.add_argument("--ttl-days", type=float, default=None, help="expire after N days")
    listing = sub.add_parser("list", help="list tokens (never shows hashes)")
    listing.add_argument("--file", required=True, help="token file path")
    listing.add_argument("--json", action="store_true", help="machine-readable output")
    revoke = sub.add_parser("revoke", help="revoke a token by id")
    revoke.add_argument("--file", required=True, help="token file path")
    revoke.add_argument("token_id", metavar="ID", help="token id, e.g. tok_1a2b3c4d")
    return parser


def _cmd_new(args: argparse.Namespace, clock: Clock) -> int:
    scopes = args.scopes or list(DEFAULT_CLI_SCOPES)
    if args.ttl_days is not None and args.ttl_days <= 0:
        print("error: --ttl-days must be positive", file=sys.stderr)
        return 2
    try:
        plaintext, record = create_token(
            args.file,
            scopes=scopes,
            label=args.label,
            ttl_days=args.ttl_days,
            clock=clock,
        )
    except SecurityConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (TokenFileError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(plaintext)
    print(f"token id: {record.id}", file=sys.stderr)
    return 0


def _cmd_list(args: argparse.Namespace, clock: Clock) -> int:
    try:
        records = list_tokens(args.file)
    except (TokenFileError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    now = clock()
    if args.json:
        print(json.dumps([r.public_json(now) for r in records], indent=2))
        return 0
    header = ("ID", "SCOPES", "LABEL", "CREATED", "EXPIRES", "STATUS")
    rows = [
        (
            r.id,
            ",".join(r.scopes),
            r.label,
            r.created_at,
            r.expires_at or "never",
            r.status(now),
        )
        for r in records
    ]
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(len(header))]
    for row in [header, *rows]:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return 0


def _cmd_revoke(args: argparse.Namespace, clock: Clock) -> int:
    try:
        found = revoke_token(args.file, args.token_id, clock=clock)
    except (TokenFileError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not found:
        print(f"error: unknown token id {args.token_id}", file=sys.stderr)
        return 1
    print(f"revoked {args.token_id}", file=sys.stderr)
    return 0


def main(argv: Sequence[str] | None = None, *, clock: Clock = time.time) -> int:
    """CLI entry point; returns the process exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    if args.command == "new":
        return _cmd_new(args, clock)
    if args.command == "list":
        return _cmd_list(args, clock)
    return _cmd_revoke(args, clock)


__all__ = [
    "FORMAT_VERSION",
    "STATUS_ACTIVE",
    "STATUS_EXPIRED",
    "STATUS_REVOKED",
    "CompositeTokenStore",
    "FileTokenStore",
    "TokenFileError",
    "TokenRecord",
    "create_token",
    "list_tokens",
    "main",
    "revoke_token",
]

if __name__ == "__main__":
    raise SystemExit(main())
