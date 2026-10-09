# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Bearer-token security core for the Grok Bot remote host.

Provides constant-time token verification (`TokenStore`), a pure-ASGI auth layer
(`AuthMiddleware`) that only ever reads the `Authorization` header, and the
bind-safety check that refuses an unauthenticated non-loopback listener.

Token values are never logged, stored, or echoed: the store keeps SHA-256 digests
only, and failure callbacks receive a reason code, never the credential. A token in
a query string is not a credential here; it is ignored, so it cannot leak into
access logs or referrers by being honoured.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

SCOPE_READ = "read"
SCOPE_CALL = "call"
SCOPE_ADMIN = "admin"
SCOPES = (SCOPE_READ, SCOPE_CALL, SCOPE_ADMIN)
MIN_TOKEN_LENGTH = 16

_SCOPE_RANK = {scope: rank for rank, scope in enumerate(SCOPES)}
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")
_REALM_HEADER = 'Bearer realm="omega-prime"'


class SecurityConfigError(ValueError):
    """A security-relevant configuration problem; callers must refuse to serve."""


@dataclass(frozen=True)
class Principal:
    """An authenticated caller. `id` is non-secret and stable."""

    id: str
    scopes: frozenset[str]
    label: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "scopes", frozenset(self.scopes))

    def allows(self, scope: str) -> bool:
        """True when a held scope covers `scope` (admin > call > read)."""
        needed = _SCOPE_RANK.get(scope)
        if needed is None:
            return False
        return any(_SCOPE_RANK.get(held, -1) >= needed for held in self.scopes)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of `token`."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(prefix: str = "omk") -> str:
    """A fresh random bearer token (256 bits of entropy)."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def parse_bearer(header: str | None) -> str | None:
    """Extract the token from `Bearer <token>`; None when absent or malformed."""
    if not header:
        return None
    scheme, sep, token = header.partition(" ")
    if not sep or scheme.lower() != "bearer":
        return None
    if not token or any(ch.isspace() for ch in token):
        return None
    return token


def _validate_scopes(scopes: Iterable[str]) -> frozenset[str]:
    held = frozenset(scopes)
    unknown = sorted(held.difference(SCOPES))
    if unknown:
        raise SecurityConfigError(
            f"unknown token scope(s): {', '.join(unknown)}; "
            f"valid scopes are {', '.join(SCOPES)}"
        )
    return held


class TokenStore:
    """Verifies presented bearer tokens against stored SHA-256 digests."""

    def __init__(self, entries: Iterable[tuple[Principal, str]] = ()) -> None:
        stored: list[tuple[Principal, str]] = []
        for principal, digest in entries:
            normalized = digest.strip().lower()
            if len(normalized) != _SHA256_HEX_LENGTH or not _HEX_DIGITS.issuperset(
                normalized
            ):
                raise SecurityConfigError(
                    f"token entry {principal.id!r} is not a SHA-256 hex digest"
                )
            _validate_scopes(principal.scopes)
            stored.append((principal, normalized))
        self._entries: tuple[tuple[Principal, str], ...] = tuple(stored)

    @classmethod
    def from_token(
        cls,
        token: str,
        *,
        principal_id: str = "env-token",
        scopes: Iterable[str] = (SCOPE_READ, SCOPE_CALL),
        label: str = "",
    ) -> TokenStore:
        """A single-token store; refuses short tokens and unknown scopes."""
        if len(token) < MIN_TOKEN_LENGTH:
            raise SecurityConfigError(
                f"bearer token is too short (minimum {MIN_TOKEN_LENGTH} characters)"
            )
        principal = Principal(principal_id, _validate_scopes(scopes), label)
        return cls([(principal, hash_token(token))])

    @property
    def enabled(self) -> bool:
        return bool(self._entries)

    def verify(self, presented: str | None) -> Principal | None:
        """The matching principal, or None.

        The presented value is hashed once and compared against EVERY stored digest
        with `hmac.compare_digest`; there is no early exit, so timing reveals neither
        which entry matched nor how many entries exist.
        """
        if not presented:
            return None
        digest = hash_token(presented).encode("ascii")
        match: Principal | None = None
        for principal, stored in self._entries:
            if hmac.compare_digest(digest, stored.encode("ascii")) and match is None:
                match = principal
        return match

    def principals(self) -> list[Principal]:
        return [principal for principal, _ in self._entries]


def is_loopback_host(host: str) -> bool:
    """True for 127.0.0.0/8, ::1 and "localhost"; wildcard binds are not loopback."""
    name = host.strip()
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    if name.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def check_bind_safety(host: str, *, auth_enabled: bool, allow_insecure: bool) -> None:
    """Refuse an unauthenticated listener on a non-loopback address."""
    if is_loopback_host(host) or auth_enabled or allow_insecure:
        return
    raise SecurityConfigError(
        f"refusing to serve on {host or '<all interfaces>'} without authentication; "
        "configure a bearer token, bind to a loopback address, or pass "
        "--allow-insecure-no-auth to accept the risk"
    )


def principal_from_scope(scope: Any) -> Principal | None:
    """The principal `AuthMiddleware` attached to an ASGI scope, if any."""
    state = scope.get("state") if hasattr(scope, "get") else None
    if state is None or not hasattr(state, "get"):
        return None
    principal = state.get("principal")
    return principal if isinstance(principal, Principal) else None


def principal_from_request(request: Any) -> Principal | None:
    """The principal on a Starlette request; tolerates None and bare objects."""
    state = getattr(request, "state", None)
    principal = getattr(state, "principal", None)
    return principal if isinstance(principal, Principal) else None


_FAILURE_DETAIL = {
    "missing": "missing bearer token",
    "malformed": "malformed Authorization header",
    "invalid": "invalid bearer token",
}


class AuthMiddleware:
    """Pure ASGI bearer authentication (never `BaseHTTPMiddleware`: it breaks SSE).

    Only the `Authorization` header is consulted. Public paths are matched exactly.
    """

    def __init__(
        self,
        app: Any,
        *,
        store: TokenStore,
        public_paths: Iterable[str] = ("/healthz", "/readyz"),
        on_failure: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.app = app
        self.store = store
        self.public_paths = frozenset(public_paths)
        self.on_failure = on_failure

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        kind = scope["type"]
        if kind == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if kind != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in self.public_paths:
            await self.app(scope, receive, send)
            return
        header = self._authorization(scope)
        reason: str | None = None
        principal: Principal | None = None
        if header is None:
            reason = "missing"
        else:
            token = parse_bearer(header)
            if token is None:
                reason = "malformed"
            else:
                principal = self.store.verify(token)
                if principal is None:
                    reason = "invalid"
        if principal is None:
            reason = reason or "invalid"
            self._report(scope, reason)
            response = JSONResponse(
                {"error": "unauthorized", "detail": _FAILURE_DETAIL[reason]},
                status_code=401,
                headers={
                    "WWW-Authenticate": _REALM_HEADER,
                    "Cache-Control": "no-store",
                },
            )
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)

    @staticmethod
    def _authorization(scope: Any) -> str | None:
        for key, value in scope.get("headers", ()):
            if key.lower() == b"authorization":
                return value.decode("latin-1")
        return None

    def _report(self, scope: Any, reason: str) -> None:
        if self.on_failure is None:
            return
        client = scope.get("client")
        event = {
            "reason": reason,
            "path": scope.get("path", ""),
            "client": client[0] if client else None,
        }
        try:
            self.on_failure(event)
        except Exception as exc:
            logger.warning("auth failure callback raised %s", type(exc).__name__)


__all__ = [
    "MIN_TOKEN_LENGTH",
    "SCOPES",
    "SCOPE_ADMIN",
    "SCOPE_CALL",
    "SCOPE_READ",
    "AuthMiddleware",
    "Principal",
    "SecurityConfigError",
    "TokenStore",
    "check_bind_safety",
    "generate_token",
    "hash_token",
    "is_loopback_host",
    "parse_bearer",
    "principal_from_request",
    "principal_from_scope",
]
