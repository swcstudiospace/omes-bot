"""SEC-NET 2.2.0 policy-bound numeric destination transport (PROPOSAL).

Registered policy authority, cancellable numeric transport and bounded
response decoding. Only this module mints AuthorityHandle, OperationIdentity,
ScopeIdentity, ConnectionIdentity, DestinationPermit and ValidatedConnection.
Copied strings/fields never confer authority.
"""

from __future__ import annotations

import contextlib
import contextvars
import gzip
import ipaddress
import re
import selectors
import socket
import ssl
import threading
import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

HeaderPairs = tuple[tuple[bytes, bytes], ...]
PublicCode = Literal[
    "invalid_url", "forbidden_host", "upstream_error", "not_configured"
]
Reason = Literal[
    "url_syntax",
    "host_policy",
    "nonpublic_answer",
    "mixed_answers",
    "resolution_empty",
    "resolution_failed",
    "resolution_malformed",
    "foreign_authority",
    "invalid_permit",
    "permit_consumed",
    "peer_mismatch",
    "tls_verification",
    "request_framing",
    "response_framing",
    "unsupported_channel",
    "unsupported_body_metadata",
    "unsupported_encoding",
    "over_bounds",
    "deadline_exceeded",
    "enforcement_attempt",
    "enforcement_channel_failed",
    "target_attachment_failed",
    "sandbox_unverified",
    "browser_exited",
    "cleanup_failed",
    "cancelled",
    "owner_died",
]

_REASON_TO_PUBLIC: dict[str, PublicCode] = {
    "url_syntax": "invalid_url",
    "host_policy": "forbidden_host",
    "nonpublic_answer": "forbidden_host",
    "mixed_answers": "forbidden_host",
    "resolution_empty": "forbidden_host",
    "resolution_malformed": "forbidden_host",
    "resolution_failed": "upstream_error",
    "foreign_authority": "not_configured",
}


@dataclass(frozen=True)
class Refusal:
    public_code: PublicCode
    internal_reason: Reason
    message: str


class DestinationDenied(Exception):
    def __init__(self, refusal: Refusal) -> None:
        super().__init__(f"{refusal.public_code}: {refusal.message}")
        self.refusal = refusal


def _deny(reason: Reason, message: str) -> DestinationDenied:
    public = _REASON_TO_PUBLIC.get(reason, "upstream_error")
    if reason in ("foreign_authority",):
        public = "not_configured"
    return DestinationDenied(Refusal(public, reason, message))


@dataclass(frozen=True)
class TransportLimits:
    request_max: int = 8_388_608
    encoded_max: int = 8_388_608
    decoded_max: int = 16_777_216
    ratio_max: int = 16
    header_count_max: int = 100
    header_bytes_max: int = 131_072
    header_line_max: int = 8_192
    request_target_max: int = 8_192
    interim_1xx_max: int = 5
    dns_records_max: int = 64
    dns_message_max: int = 65_536
    resolver_memory_max: int = 134_217_728
    exchange_deadline_s: float = 30.0
    preview_deadline_s: float = 15.0
    preview_sample_max: int = 2_000_000
    io_chunk_max: int = 65_536
    decoder_workspace_max: int = 262_144


class AuthorityHandle:
    __slots__ = ("_transport_id",)

    def __init__(self, transport_id: int) -> None:
        object.__setattr__(self, "_transport_id", transport_id)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("AuthorityHandle is immutable")

    def __repr__(self) -> str:
        return "AuthorityHandle(<private>)"


class ScopeIdentity:
    __slots__ = ("_token",)
    _token: object

    def __init__(self, token: object) -> None:
        object.__setattr__(self, "_token", token)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("ScopeIdentity is immutable")


class ConnectionIdentity:
    __slots__ = ("_token",)
    _token: object

    def __init__(self, token: object) -> None:
        object.__setattr__(self, "_token", token)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("ConnectionIdentity is immutable")


class OperationIdentity:
    __slots__ = ("_token",)
    _token: object

    def __init__(self, token: object) -> None:
        object.__setattr__(self, "_token", token)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("OperationIdentity is immutable")


class AbortSubscription:
    __slots__ = ("_handle", "_token")
    _handle: AbortHandle
    _token: object

    def __init__(self, token: object, handle: AbortHandle) -> None:
        object.__setattr__(self, "_handle", handle)
        object.__setattr__(self, "_token", token)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("AbortSubscription is immutable")


class AbortHandle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reason: Reason | None = None
        self._callbacks: dict[int, Callable[[Reason], None]] = {}
        self._next = 0

    def abort(self, reason: Reason = "cancelled") -> None:
        with self._lock:
            if self._reason is not None:
                return
            self._reason = reason
            callbacks = list(self._callbacks.values())
        for cb in callbacks:
            with contextlib.suppress(Exception):
                cb(reason)

    @property
    def reason(self) -> Reason | None:
        with self._lock:
            return self._reason

    def subscribe(self, callback: Callable[[Reason], None]) -> AbortSubscription:
        with self._lock:
            if self._reason is not None:
                reason = self._reason
            else:
                token = object()
                sub = AbortSubscription(token, self)
                self._callbacks[id(token)] = callback
                return sub
        callback(reason)
        token = object()
        return AbortSubscription(token, self)

    def unsubscribe(self, subscription: AbortSubscription) -> None:
        with self._lock:
            self._callbacks.pop(id(subscription._token), None)


@dataclass(frozen=True)
class OperationDrain:
    operation: OperationIdentity
    scopes_closed: int
    pending_scopes: int
    abort_reason: Reason | None
    errors: tuple[str, ...]
    complete: bool


class RootOperation:
    identity: OperationIdentity
    authority: AuthorityHandle
    deadline_at: float
    abort_handle: AbortHandle
    _transport: DestinationTransport

    def __init__(
        self,
        identity: OperationIdentity,
        authority: AuthorityHandle,
        deadline_at: float,
        abort_handle: AbortHandle,
        transport: DestinationTransport,
    ) -> None:
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "deadline_at", deadline_at)
        object.__setattr__(self, "abort_handle", abort_handle)
        object.__setattr__(self, "_transport", transport)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("RootOperation fields are immutable")

    @property
    def drain(self) -> OperationDrain | None:
        return self._transport._drain_of(self)

    def remaining(self) -> float:
        if self.abort_handle.reason is not None:
            raise DestinationDenied(_deny("cancelled", "operation aborted").refusal)
        if self._transport._finished(self):
            raise DestinationDenied(_deny("cancelled", "operation finished").refusal)
        left = self.deadline_at - self._transport._clock.monotonic()
        if left <= 0:
            raise DestinationDenied(
                _deny("deadline_exceeded", "operation expired").refusal
            )
        return left


class OperationBinding:
    def __init__(
        self, transport: DestinationTransport, operation: RootOperation, token: Any
    ) -> None:
        self._transport = transport
        self._operation = operation
        self._token = token

    def __enter__(self) -> RootOperation:
        return self._operation

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._transport._reset_operation(self._token)


class OperationScope:
    def __init__(
        self,
        identity: ScopeIdentity,
        operation: RootOperation,
        parent: OperationScope | None,
        deadline_at: float,
        abort_handle: AbortHandle,
        transport: DestinationTransport,
    ) -> None:
        self.identity = identity
        self.operation = operation
        self.parent = parent
        self.deadline_at = deadline_at
        self.abort_handle = abort_handle
        self._transport = transport
        self._closed = False

    def remaining(self) -> float:
        if self._closed:
            raise DestinationDenied(_deny("cancelled", "scope closed").refusal)
        if self.abort_handle.reason is not None:
            raise DestinationDenied(_deny("cancelled", "scope aborted").refusal)
        self.operation.remaining()
        left = self.deadline_at - self._transport._clock.monotonic()
        if left <= 0:
            raise DestinationDenied(_deny("deadline_exceeded", "scope expired").refusal)
        return left

    def close(self) -> None:
        self._transport._close_scope(self)


@dataclass(frozen=True)
class ParsedURL:
    input_url: str
    browser_url: str
    scheme: Literal["http", "https"]
    host_key: str
    port: int
    http_authority: str
    request_target: str
    tls_identity: str


@dataclass(frozen=True)
class ResolvedAddress:
    family: Literal[2, 10]
    address: str
    port: int
    socktype: Literal[1] = 1
    protocol: Literal[6] = 6
    flowinfo: Literal[0] = 0
    scope_id: Literal[0] = 0


@dataclass(frozen=True)
class HttpRequest:
    url: str
    method: str
    headers: HeaderPairs = ()
    body: bytes | None = None


class Resolver:
    def resolve(
        self, host: str, port: int, *, scope: OperationScope, limits: TransportLimits
    ) -> tuple[ResolvedAddress, ...]:
        infos = socket.getaddrinfo(
            host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP, 0
        )
        out: list[ResolvedAddress] = []
        for fam, _st, _proto, _, sockaddr in infos[: limits.dns_records_max]:
            family: Literal[2, 10] = 2 if fam == socket.AF_INET else 10
            addr = str(sockaddr[0])
            out.append(ResolvedAddress(family=family, address=addr, port=port))
        return tuple(out)


class _SocketAdapter:
    family: int

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self.family = sock.family

    def getpeername(self):  # type: ignore[no-untyped-def]
        return self._sock.getpeername()

    def setblocking(self, flag: bool) -> None:
        self._sock.setblocking(flag)

    def fileno(self) -> int:
        return self._sock.fileno()

    def send(self, data: memoryview) -> int:
        return self._sock.send(data)

    def recv_into(self, buffer: memoryview) -> int:
        return self._sock.recv_into(buffer)

    def shutdown(self, how: int) -> None:
        with contextlib.suppress(OSError):
            self._sock.shutdown(how)

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._sock.close()


class NumericDialer:
    def dial(
        self, endpoint: ResolvedAddress, *, scope: OperationScope
    ) -> _SocketAdapter:
        remaining = scope.remaining()
        fam = socket.AF_INET if endpoint.family == 2 else socket.AF_INET6
        sock = socket.socket(fam, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        try:
            sock.settimeout(max(0.001, remaining))
            sock.connect((endpoint.address, endpoint.port))
            sock.settimeout(None)
        except Exception:
            with contextlib.suppress(OSError):
                sock.close()
            raise DestinationDenied(
                _deny("resolution_failed", "connection failed").refusal
            ) from None
        return _SocketAdapter(sock)


class TLSVerifier:
    def wrap(
        self, raw: Any, *, identity: str, context: ssl.SSLContext, scope: OperationScope
    ) -> Any:
        try:
            wrapped_sock = context.wrap_socket(
                raw._sock,
                server_hostname=None if _is_ip_literal(identity) else identity,
            )
            if _is_ip_literal(identity):
                match_fn = getattr(ssl, "match_hostname", None)
                if callable(match_fn):
                    match_fn(wrapped_sock.getpeercert() or {}, identity)
        except DestinationDenied:
            raise
        except Exception:
            raise DestinationDenied(
                _deny("tls_verification", "TLS verification failed").refusal
            ) from None
        return _SocketAdapter(wrapped_sock)


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class DestinationPermit:
    authority: AuthorityHandle
    policy_identity: object
    scope_identity: ScopeIdentity
    request: HttpRequest
    parsed: ParsedURL
    admitted_addresses: tuple[ResolvedAddress, ...]
    selected: ResolvedAddress
    nonce: object
    issued_at: float
    expires_at: float

    def __init__(
        self,
        authority: AuthorityHandle,
        policy_identity: object,
        scope_identity: ScopeIdentity,
        request: HttpRequest,
        parsed: ParsedURL,
        admitted_addresses: tuple[ResolvedAddress, ...],
        selected: ResolvedAddress,
        nonce: object,
        issued_at: float,
        expires_at: float,
    ) -> None:
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "policy_identity", policy_identity)
        object.__setattr__(self, "scope_identity", scope_identity)
        object.__setattr__(self, "request", request)
        object.__setattr__(self, "parsed", parsed)
        object.__setattr__(self, "admitted_addresses", admitted_addresses)
        object.__setattr__(self, "selected", selected)
        object.__setattr__(self, "nonce", nonce)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("DestinationPermit is immutable")


class ValidatedConnection:
    def __init__(
        self,
        identity: ConnectionIdentity,
        authority: AuthorityHandle,
        permit: DestinationPermit,
        scope_identity: ScopeIdentity,
        peer: ResolvedAddress,
        tls_identity: str | None,
        raw: Any,
        wrapped: Any | None,
        transport: DestinationTransport,
    ) -> None:
        self.identity = identity
        self.authority = authority
        self.permit = permit
        self.scope_identity = scope_identity
        self.peer = peer
        self.tls_identity = tls_identity
        self._raw = raw
        self._wrapped = wrapped
        self._transport = transport
        self._closed = False

    def abort(self, reason: Reason = "cancelled") -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for sock in (self._wrapped, self._raw):
            if sock is not None:
                with contextlib.suppress(Exception):
                    sock.close()
        self._transport._unregister_connection(self)

    def __enter__(self) -> ValidatedConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


@dataclass(frozen=True)
class SafeResponse:
    url: str
    status: int
    reason: bytes
    headers: HeaderPairs
    body: bytes
    content_encoding: Literal["identity", "gzip", "deflate"]
    body_complete: bool
    sample_limit: int | None
    elapsed_ms: float


@dataclass(frozen=True)
class DecodeBudget:
    decoded_max: int
    base64_max: int
    scratch_max: int


@dataclass(frozen=True)
class DecodedResponse:
    url: str
    status: int
    reason: bytes
    headers: HeaderPairs
    body: bytes
    body_kind: Literal["entity", "head", "no_content", "not_modified"]
    body_complete: Literal[True]
    encoded_bytes: int
    decoded_bytes: int
    base64_bytes: int


_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_IPV4_CANON = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")

_V4_EXCLUDED = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]
_V6_EXCLUDED = [
    ipaddress.ip_network("::/96"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
    ipaddress.ip_network("2001::/23"),
    ipaddress.ip_network("2002::/16"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("2001:db8::/32"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
]


def _address_admitted(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv4Address):
        if not ip.is_global:
            return False
        return not any(ip in net for net in _V4_EXCLUDED)
    if ip.ipv4_mapped is not None or ip.sixtofour is not None or ip.teredo is not None:
        return False
    if (
        ip.is_multicast
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    try:
        if not ip.is_global:
            return False
    except Exception:
        return False
    return not any(ip in net for net in _V6_EXCLUDED)


def parse_url(input_url: str) -> ParsedURL:
    if not isinstance(input_url, str) or not input_url:
        raise DestinationDenied(
            _deny("url_syntax", "URL must be a non-empty string").refusal
        )
    if any(ord(c) < 32 or ord(c) == 127 for c in input_url):
        raise DestinationDenied(
            _deny("url_syntax", "URL contains control characters").refusal
        )
    try:
        parts = urlsplit(input_url)
    except ValueError:
        raise DestinationDenied(
            _deny("url_syntax", "URL cannot be parsed").refusal
        ) from None
    if parts.scheme not in ("http", "https"):
        raise DestinationDenied(
            _deny("url_syntax", "only http and https URLs are allowed").refusal
        )
    if parts.username or parts.password or "@" in (parts.netloc or ""):
        raise DestinationDenied(
            _deny("url_syntax", "URL userinfo is not allowed").refusal
        )
    raw_netloc = parts.netloc or ""
    raw_host = parts.hostname or ""
    if not raw_host:
        raise DestinationDenied(_deny("url_syntax", "URL has no host").refusal)
    # urlsplit strips a trailing dot from hostname; the raw authority must still refuse.
    raw_name = raw_netloc
    if raw_name.startswith("[") and "]" in raw_name:
        raw_name = raw_name[1 : raw_name.index("]")]
    else:
        raw_name = raw_name.split(":", 1)[0]
    if raw_name.endswith(".") or raw_host.endswith("."):
        raise DestinationDenied(_deny("url_syntax", "host has a trailing dot").refusal)
    if "\\" in input_url.split("://", 1)[-1].split("/", 1)[0]:
        raise DestinationDenied(
            _deny("url_syntax", "authority contains a backslash").refusal
        )
    if any(c.isspace() for c in (parts.netloc or "")):
        raise DestinationDenied(
            _deny("url_syntax", "authority contains whitespace").refusal
        )
    if "%" in (parts.netloc or ""):
        raise DestinationDenied(
            _deny("url_syntax", "authority contains percent escapes").refusal
        )
    host_key = raw_host.lower()
    if host_key.endswith(".") or not host_key:
        raise DestinationDenied(_deny("url_syntax", "host has a trailing dot").refusal)
    try:
        host_key.encode("ascii")
    except UnicodeEncodeError:
        raise DestinationDenied(
            _deny("url_syntax", "host must be ASCII punycode").refusal
        ) from None
    if ":" in host_key and not (parts.netloc or "").startswith("["):
        raise DestinationDenied(
            _deny("url_syntax", "IPv6 host must be bracketed").refusal
        )
    if _is_ip_literal(host_key):
        try:
            ip = ipaddress.ip_address(host_key)
        except ValueError:
            raise DestinationDenied(
                _deny("url_syntax", "malformed numeric host").refusal
            ) from None
        if isinstance(ip, ipaddress.IPv4Address):
            m = _IPV4_CANON.match(host_key)
            if not m or any(len(g) > 1 and g.startswith("0") for g in m.groups()):
                raise DestinationDenied(
                    _deny("url_syntax", "IPv4 host is not canonical").refusal
                )
            if str(ip) != host_key:
                raise DestinationDenied(
                    _deny("url_syntax", "IPv4 host is not canonical").refusal
                )
        else:
            if host_key != ip.compressed.lower():
                raise DestinationDenied(
                    _deny("url_syntax", "IPv6 host is not canonical").refusal
                )
            if getattr(ip, "scope_id", None):
                raise DestinationDenied(
                    _deny("url_syntax", "IPv6 zone is not allowed").refusal
                )
    try:
        explicit_port = parts.port
    except ValueError:
        raise DestinationDenied(_deny("url_syntax", "malformed port").refusal) from None
    if explicit_port is None:
        port = 443 if parts.scheme == "https" else 80
    else:
        port = explicit_port
    if not 1 <= port <= 65535:
        raise DestinationDenied(_deny("url_syntax", "port is out of range").refusal)
    path = parts.path or "/"
    target = path + (("?" + parts.query) if parts.query else "")
    try:
        target.encode("ascii")
    except UnicodeEncodeError:
        raise DestinationDenied(
            _deny("url_syntax", "request target must be ASCII").refusal
        ) from None
    if any(ord(c) < 32 or ord(c) == 127 or c == " " for c in target):
        raise DestinationDenied(
            _deny("url_syntax", "request target has bad characters").refusal
        )
    if len(target.encode("ascii")) > 8_192:
        raise DestinationDenied(
            _deny("url_syntax", "request target is oversized").refusal
        )
    if not target.startswith("/"):
        raise DestinationDenied(
            _deny("url_syntax", "request target must be origin-form").refusal
        )
    default_port = 443 if parts.scheme == "https" else 80
    if ":" in host_key and not host_key.startswith("["):
        http_authority = (
            f"[{host_key}]" if port == default_port else f"[{host_key}]:{port}"
        )
    else:
        http_authority = host_key if port == default_port else f"{host_key}:{port}"
    return ParsedURL(
        input_url=input_url,
        browser_url=input_url,
        scheme=parts.scheme,  # type: ignore[arg-type]
        host_key=host_key,
        port=port,
        http_authority=http_authority,
        request_target=target,
        tls_identity=host_key,
    )


def _validate_headers(headers: HeaderPairs, limits: TransportLimits) -> None:
    if len(headers) > limits.header_count_max:
        raise DestinationDenied(_deny("request_framing", "too many headers").refusal)
    seen_host = 0
    seen_cl: list[bytes] = []
    seen_te = False
    for name, value in headers:
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise DestinationDenied(
                _deny("request_framing", "headers must be bytes").refusal
            )
        try:
            text = name.decode("ascii")
        except UnicodeDecodeError:
            raise DestinationDenied(
                _deny("request_framing", "header name must be ASCII").refusal
            ) from None
        if not _TOKEN_RE.match(text):
            raise DestinationDenied(
                _deny("request_framing", "header name is not a token").refusal
            )
        if b"\x00" in value or b"\r" in value or b"\n" in value:
            raise DestinationDenied(
                _deny("request_framing", "header value has bad bytes").refusal
            )
        lowered = text.lower()
        if lowered == "host":
            seen_host += 1
        if lowered == "content-length":
            seen_cl.append(value.strip())
        if lowered == "transfer-encoding":
            seen_te = True
    if seen_host > 1:
        raise DestinationDenied(
            _deny("request_framing", "multiple Host headers").refusal
        )
    if len(set(seen_cl)) > 1:
        raise DestinationDenied(
            _deny("request_framing", "conflicting Content-Length").refusal
        )
    if seen_cl and seen_te:
        raise DestinationDenied(
            _deny("request_framing", "Content-Length with Transfer-Encoding").refusal
        )


class _Clock:
    def monotonic(self) -> float:
        return time.monotonic()


_DEFAULT_LIMITS = TransportLimits()


class DestinationTransport:
    def __init__(
        self,
        policy: Any | None,
        *,
        resolver: Any | None = None,
        dialer: Any | None = None,
        tls_verifier: Any | None = None,
        tls_context: ssl.SSLContext | None = None,
        clock: Any | None = None,
        limits: TransportLimits = _DEFAULT_LIMITS,
    ) -> None:
        self._policy = policy
        self._resolver = resolver or Resolver()
        self._dialer = dialer or NumericDialer()
        self._tls_verifier = tls_verifier or TLSVerifier()
        if tls_context is not None:
            self._tls_context = tls_context
        else:
            ctx = ssl.create_default_context()
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            with contextlib.suppress(Exception):
                ctx.set_alpn_protocols(["http/1.1"])
            self._tls_context = ctx
        self._clock = clock or _Clock()
        self._limits = limits
        self._authority = AuthorityHandle(id(self))
        self._lock = threading.RLock()
        self._current: contextvars.ContextVar = contextvars.ContextVar(
            "omega_prime_operation", default=None
        )
        self._roots: dict[int, RootOperation] = {}
        self._root_finished: set[int] = set()
        self._drains: dict[int, OperationDrain] = {}
        self._scopes: dict[int, OperationScope] = {}
        self._scope_open: set[int] = set()
        self._permits: dict[int, dict[str, Any]] = {}
        self._connections: dict[int, ValidatedConnection] = {}
        self._exchanges: dict[int, dict[str, Any]] = {}
        self._policy_identity = object()

    @property
    def authority(self) -> AuthorityHandle:
        return self._authority

    @property
    def policy(self) -> Any | None:
        return self._policy

    @property
    def limits(self) -> TransportLimits:
        return self._limits

    def begin_operation(self, *, deadline_at: float) -> RootOperation:
        now = self._clock.monotonic()
        if not isinstance(deadline_at, (int, float)) or deadline_at != deadline_at:
            raise DestinationDenied(
                _deny("deadline_exceeded", "deadline must be finite").refusal
            )
        if deadline_at <= now or deadline_at - now > 3_600:
            raise DestinationDenied(
                _deny(
                    "deadline_exceeded", "deadline must be a finite future time"
                ).refusal
            )
        identity = OperationIdentity(object())
        root = RootOperation(
            identity, self._authority, float(deadline_at), AbortHandle(), self
        )
        with self._lock:
            self._roots[id(identity._token)] = root
        return root

    def bind_operation(self, operation: RootOperation) -> OperationBinding:
        if operation.authority is not self._authority:
            raise DestinationDenied(
                _deny("foreign_authority", "foreign operation authority").refusal
            )
        with self._lock:
            if id(operation.identity._token) not in self._roots:
                raise DestinationDenied(
                    _deny("foreign_authority", "unknown operation").refusal
                )
            if id(operation.identity._token) in self._root_finished:
                raise DestinationDenied(
                    _deny("cancelled", "operation is finished").refusal
                )
            current = self._current.get()
            if current is not None and current is not operation:
                raise DestinationDenied(
                    _deny("foreign_authority", "conflicting bound operation").refusal
                )
            token = self._current.set(operation)
        return OperationBinding(self, operation, token)

    def current_operation(self) -> RootOperation | None:
        current = self._current.get()
        if current is None:
            return None
        with self._lock:
            if id(current.identity._token) not in self._roots:
                return None
            if id(current.identity._token) in self._root_finished:
                return None
        return current

    def _reset_operation(self, token: Any) -> None:
        self._current.reset(token)

    def _finished(self, root: RootOperation) -> bool:
        with self._lock:
            return id(root.identity._token) in self._root_finished

    def _drain_of(self, root: RootOperation) -> OperationDrain | None:
        with self._lock:
            return self._drains.get(id(root.identity._token))

    def finish_operation(
        self, operation: RootOperation, *, deadline_at: float
    ) -> OperationDrain:
        if operation.authority is not self._authority:
            raise DestinationDenied(
                _deny("foreign_authority", "foreign operation authority").refusal
            )
        with self._lock:
            key = id(operation.identity._token)
            if key not in self._roots:
                raise DestinationDenied(
                    _deny("foreign_authority", "unknown operation").refusal
                )
            if key in self._drains:
                return self._drains[key]
            pending = sum(
                1
                for skey in self._scope_open
                if self._scopes.get(skey) is not None
                and self._scopes[skey].operation is operation
            )
            for _skey, scope in list(self._scopes.items()):
                if scope.operation is operation:
                    scope._closed = True
            self._scope_open = {
                s
                for s in self._scope_open
                if self._scopes.get(s) is None
                or self._scopes[s].operation is not operation
            }
            for _ckey, conn in list(self._connections.items()):
                if (
                    conn.permit.scope_identity is not None
                    and self._scopes.get(id(conn.scope_identity._token)) is not None
                ):
                    pass
            self._root_finished.add(key)
            drain = OperationDrain(
                operation=operation.identity,
                scopes_closed=0,
                pending_scopes=0,
                abort_reason=operation.abort_handle.reason,
                errors=(),
                complete=(pending == 0 and operation.abort_handle.reason is None),
            )
            if pending or operation.abort_handle.reason is not None:
                drain = OperationDrain(
                    operation=operation.identity,
                    scopes_closed=0,
                    pending_scopes=pending,
                    abort_reason=operation.abort_handle.reason,
                    errors=(),
                    complete=False,
                )
            self._drains[key] = drain
            return drain

    def open_scope(
        self,
        *,
        operation: RootOperation,
        deadline_at: float,
        parent: OperationScope | None = None,
    ) -> OperationScope:
        if operation.authority is not self._authority:
            raise DestinationDenied(
                _deny("foreign_authority", "foreign operation authority").refusal
            )
        with self._lock:
            key = id(operation.identity._token)
            if key not in self._roots or key in self._root_finished:
                raise DestinationDenied(
                    _deny("foreign_authority", "operation is not live").refusal
                )
            if operation.abort_handle.reason is not None:
                raise DestinationDenied(
                    _deny("cancelled", "operation is aborted").refusal
                )
            if parent is not None:
                pkey = id(parent.identity._token)
                if pkey not in self._scopes or pkey not in self._scope_open:
                    raise DestinationDenied(
                        _deny("foreign_authority", "parent scope is not live").refusal
                    )
                if parent.operation is not operation:
                    raise DestinationDenied(
                        _deny(
                            "foreign_authority", "parent belongs to another operation"
                        ).refusal
                    )
                if parent.abort_handle.reason is not None:
                    raise DestinationDenied(
                        _deny("cancelled", "parent scope is aborted").refusal
                    )
                cap = min(operation.deadline_at, parent.deadline_at, deadline_at)
            else:
                cap = min(operation.deadline_at, deadline_at)
            identity = ScopeIdentity(object())
            child_abort = AbortHandle()
            parent_handle = (
                parent.abort_handle if parent is not None else operation.abort_handle
            )
            if parent_handle.reason is not None:
                raise DestinationDenied(_deny("cancelled", "parent is aborted").refusal)
            scope = OperationScope(
                identity, operation, parent, float(cap), child_abort, self
            )
            skey = id(identity._token)
            self._scopes[skey] = scope
            self._scope_open.add(skey)

            def _propagate(
                reason: Reason, _child_abort: AbortHandle = child_abort
            ) -> None:
                _child_abort.abort(reason)

            sub = parent_handle.subscribe(_propagate)
            scope._parent_sub = sub  # type: ignore[attr-defined]
            scope._parent_handle = parent_handle  # type: ignore[attr-defined]
            return scope

    def _close_scope(self, scope: OperationScope) -> None:
        with self._lock:
            skey = id(scope.identity._token)
            if skey not in self._scope_open:
                return
            self._scope_open.discard(skey)
            scope._closed = True
            parent_handle = getattr(scope, "_parent_handle", None)
            sub = getattr(scope, "_parent_sub", None)
            if parent_handle is not None and sub is not None:
                with contextlib.suppress(Exception):
                    parent_handle.unsubscribe(sub)

    def _unregister_connection(self, conn: ValidatedConnection) -> None:
        with self._lock:
            self._connections.pop(id(conn.identity._token), None)

    def admit(
        self, request: HttpRequest, *, scope: OperationScope
    ) -> DestinationPermit:
        scope.remaining()
        with self._lock:
            if id(scope.identity._token) not in self._scope_open:
                raise DestinationDenied(
                    _deny("foreign_authority", "scope is not live").refusal
                )
        if (
            not isinstance(request.method, str)
            or not request.method
            or not _TOKEN_RE.match(request.method)
        ):
            raise DestinationDenied(
                _deny("request_framing", "method is not a token").refusal
            )
        if request.method.upper() not in ("GET", "HEAD"):
            raise DestinationDenied(
                _deny("request_framing", "only GET and HEAD are supported").refusal
            )
        _validate_headers(request.headers, self._limits)
        if request.body is not None:
            if not isinstance(request.body, bytes):
                raise DestinationDenied(
                    _deny("request_framing", "body must be bytes").refusal
                )
            if len(request.body) > self._limits.request_max:
                raise DestinationDenied(
                    _deny("over_bounds", "body exceeds request_max").refusal
                )
        parsed = parse_url(request.url)
        policy = self._policy
        if policy is None:
            raise DestinationDenied(
                _deny("host_policy", "no policy is configured").refusal
            )
        try:
            allowed = policy.allows_host(parsed.host_key)
        except Exception:
            raise DestinationDenied(
                _deny("host_policy", "policy check failed").refusal
            ) from None
        if not allowed:
            raise DestinationDenied(_deny("host_policy", "host is not allowed").refusal)
        try:
            answers = self._resolver.resolve(
                parsed.host_key, parsed.port, scope=scope, limits=self._limits
            )
        except DestinationDenied:
            raise
        except Exception:
            raise DestinationDenied(
                _deny("resolution_failed", "resolution failed").refusal
            ) from None
        if not answers:
            raise DestinationDenied(
                _deny("resolution_empty", "resolution returned no records").refusal
            )
        if len(answers) > self._limits.dns_records_max:
            raise DestinationDenied(
                _deny("over_bounds", "too many DNS records").refusal
            )
        admitted: list[ResolvedAddress] = []
        saw_bad = False
        for rec in answers:
            try:
                fam = rec.family
                port_ok = rec.port == parsed.port
                proto_ok = rec.socktype == 1 and rec.protocol == 6 and fam in (2, 10)
                addr_ok = _address_admitted(rec.address)
            except Exception:
                saw_bad = True
                continue
            if not (port_ok and proto_ok and addr_ok):
                saw_bad = True
                continue
            admitted.append(rec)
        if not admitted:
            raise DestinationDenied(
                _deny("nonpublic_answer", "no admitted address").refusal
            )
        if saw_bad:
            raise DestinationDenied(
                _deny(
                    "mixed_answers", "answer set mixes admitted and refused records"
                ).refusal
            )
        selected = admitted[0]
        nonce = object()
        now = self._clock.monotonic()
        permit = DestinationPermit(
            authority=self._authority,
            policy_identity=self._policy_identity,
            scope_identity=scope.identity,
            request=request,
            parsed=parsed,
            admitted_addresses=tuple(admitted),
            selected=selected,
            nonce=nonce,
            issued_at=now,
            expires_at=min(scope.deadline_at, scope.operation.deadline_at),
        )
        with self._lock:
            self._permits[id(nonce)] = {"permit": permit, "consumed": False}
        return permit

    def connect(
        self, permit: DestinationPermit, *, scope: OperationScope
    ) -> ValidatedConnection:
        scope.remaining()
        if permit.authority is not self._authority:
            raise DestinationDenied(
                _deny("foreign_authority", "foreign permit authority").refusal
            )
        with self._lock:
            if id(scope.identity._token) not in self._scope_open:
                raise DestinationDenied(
                    _deny("foreign_authority", "scope is not live").refusal
                )
            record = self._permits.get(id(permit.nonce))
            if record is None:
                raise DestinationDenied(
                    _deny("invalid_permit", "permit is not registered").refusal
                )
            if record["consumed"]:
                raise DestinationDenied(
                    _deny("permit_consumed", "permit was already used").refusal
                )
            record["consumed"] = True
            stored: DestinationPermit = record["permit"]
            if stored is not permit:
                raise DestinationDenied(
                    _deny("invalid_permit", "permit copy is not authorized").refusal
                )
            if stored.scope_identity._token is not scope.identity._token:
                raise DestinationDenied(
                    _deny("invalid_permit", "permit belongs to another scope").refusal
                )
            now = self._clock.monotonic()
            if now > stored.expires_at:
                raise DestinationDenied(
                    _deny("invalid_permit", "permit has expired").refusal
                )
        raw = self._dialer.dial(permit.selected, scope=scope)
        try:
            peer = raw.getpeername()
            peer_addr = peer[0]
            peer_port = peer[1]
            peer_norm = peer_addr.lower() if isinstance(peer_addr, str) else peer_addr
            sel_norm = permit.selected.address.lower()
            if (
                peer_norm != sel_norm
                or peer_port != permit.selected.port
                or raw.family not in (2, 10)
            ):
                raise DestinationDenied(
                    _deny("peer_mismatch", "peer does not match permit").refusal
                )
            wrapped = None
            tls_identity: str | None = None
            if permit.parsed.scheme == "https":
                wrapped = self._tls_verifier.wrap(
                    raw,
                    identity=permit.parsed.tls_identity,
                    context=self._tls_context,
                    scope=scope,
                )
                try:
                    wpeer = wrapped.getpeername()
                    if (
                        wpeer[0].lower() if isinstance(wpeer[0], str) else wpeer[0]
                    ) != sel_norm or wpeer[1] != permit.selected.port:
                        raise DestinationDenied(
                            _deny(
                                "peer_mismatch", "TLS peer does not match permit"
                            ).refusal
                        )
                except DestinationDenied:
                    with contextlib.suppress(Exception):
                        wrapped.close()
                    raise
                tls_identity = permit.parsed.tls_identity
        except DestinationDenied:
            with contextlib.suppress(Exception):
                raw.close()
            raise
        except Exception:
            with contextlib.suppress(Exception):
                raw.close()
            raise DestinationDenied(
                _deny("peer_mismatch", "peer check failed").refusal
            ) from None
        identity = ConnectionIdentity(object())
        conn = ValidatedConnection(
            identity,
            self._authority,
            permit,
            scope.identity,
            permit.selected,
            tls_identity,
            raw,
            wrapped,
            self,
        )
        with self._lock:
            self._connections[id(identity._token)] = conn
        return conn

    def exchange(
        self,
        connection: ValidatedConnection,
        request: HttpRequest,
        *,
        scope: OperationScope,
        sample_limit: int | None = None,
    ) -> SafeResponse:
        started = self._clock.monotonic()
        scope.remaining()
        if connection.authority is not self._authority:
            raise DestinationDenied(
                _deny("foreign_authority", "foreign connection").refusal
            )
        with self._lock:
            if id(scope.identity._token) not in self._scope_open:
                raise DestinationDenied(
                    _deny("foreign_authority", "scope is not live").refusal
                )
            if id(connection.identity._token) not in self._connections:
                raise DestinationDenied(
                    _deny("invalid_permit", "connection is not registered").refusal
                )
            if connection.permit.request is not request:
                raise DestinationDenied(
                    _deny("invalid_permit", "request does not match permit").refusal
                )
            if connection.scope_identity._token is not scope.identity._token:
                raise DestinationDenied(
                    _deny(
                        "invalid_permit", "connection belongs to another scope"
                    ).refusal
                )
        _validate_headers(request.headers, self._limits)
        parsed = connection.permit.parsed
        read_cap = self._limits.encoded_max if sample_limit is None else sample_limit
        sock = (
            connection._wrapped if connection._wrapped is not None else connection._raw
        )
        wire = _serialize_request(request, parsed)
        if len(wire) > self._limits.request_max:
            raise DestinationDenied(
                _deny("over_bounds", "serialized request is oversized").refusal
            )
        _send_all(sock, wire, scope, self._limits)
        status, reason, headers, body, complete, encoding = _read_response(
            sock, scope, self._limits, read_cap, request.method.upper()
        )
        if sample_limit is not None and len(body) >= sample_limit:
            complete = False
        elapsed = (self._clock.monotonic() - started) * 1000.0
        response = SafeResponse(
            url=request.url,
            status=status,
            reason=reason,
            headers=headers,
            body=body,
            content_encoding=encoding,
            body_complete=complete,
            sample_limit=sample_limit,
            elapsed_ms=elapsed,
        )
        with self._lock:
            self._exchanges[id(response)] = {
                "request": request,
                "scope": id(scope.identity._token),
                "operation": id(scope.operation.identity._token),
                "decode_used": False,
                "sample_limit": sample_limit,
                "complete": complete,
            }
            self._response_scope = getattr(self, "_response_scope", {})
            self._response_scope[id(response)] = scope
        return response

    def fetch(
        self,
        request: HttpRequest,
        *,
        scope: OperationScope,
        sample_limit: int | None = None,
    ) -> SafeResponse:
        permit = self.admit(request, scope=scope)
        conn = self.connect(permit, scope=scope)
        try:
            return self.exchange(conn, request, scope=scope, sample_limit=sample_limit)
        finally:
            conn.close()

    def decode_response(
        self,
        response: SafeResponse,
        *,
        request: HttpRequest,
        scope: OperationScope,
        budget: DecodeBudget,
    ) -> DecodedResponse:
        scope.remaining()
        for field in ("decoded_max", "base64_max", "scratch_max"):
            value = getattr(budget, field)
            if isinstance(value, bool) or not isinstance(value, int):
                raise DestinationDenied(
                    _deny("over_bounds", "decode budget must be integers").refusal
                )
            if value < 0:
                raise DestinationDenied(
                    _deny("over_bounds", "decode budget is negative").refusal
                )
        if budget.decoded_max > self._limits.decoded_max or budget.base64_max > 4 * (
            (self._limits.decoded_max + 2) // 3
        ):
            raise DestinationDenied(
                _deny("over_bounds", "decode budget exceeds transport limits").refusal
            )
        if budget.scratch_max < self._limits.decoder_workspace_max:
            raise DestinationDenied(
                _deny("over_bounds", "decoder workspace reservation is missing").refusal
            )
        with self._lock:
            record = self._exchanges.get(id(response))
            if record is None:
                raise DestinationDenied(
                    _deny(
                        "foreign_authority", "response is not a registered exchange"
                    ).refusal
                )
            if record["decode_used"]:
                raise DestinationDenied(
                    _deny(
                        "permit_consumed", "decode authorization was consumed"
                    ).refusal
                )
            if record["request"] is not request:
                raise DestinationDenied(
                    _deny(
                        "foreign_authority", "request does not match exchange"
                    ).refusal
                )
            if record["scope"] != id(scope.identity._token):
                raise DestinationDenied(
                    _deny("foreign_authority", "scope does not match exchange").refusal
                )
            if id(scope.identity._token) not in self._scope_open:
                raise DestinationDenied(
                    _deny("foreign_authority", "scope is not live").refusal
                )
            record["decode_used"] = True
        if response.sample_limit is not None or not response.body_complete:
            raise DestinationDenied(
                _deny("response_framing", "sampled response is not decodable").refusal
            )
        decoded_max = min(budget.decoded_max, self._limits.decoded_max)
        body_kind, decoded = _decode_body(response, request, decoded_max, self._limits)
        decoded_bytes = len(decoded)
        base64_bytes = 4 * ((decoded_bytes + 2) // 3)
        if base64_bytes > budget.base64_max:
            raise DestinationDenied(
                _deny("over_bounds", "base64 output exceeds budget").refusal
            )
        headers = _decoded_headers(
            response.headers,
            response.status,
            request.method.upper(),
            body_kind,
            decoded_bytes,
        )
        return DecodedResponse(
            url=response.url,
            status=response.status,
            reason=response.reason,
            headers=headers,
            body=decoded,
            body_kind=body_kind,
            body_complete=True,
            encoded_bytes=len(response.body),
            decoded_bytes=decoded_bytes,
            base64_bytes=base64_bytes,
        )


_HOP_BY_HOP = {
    "connection",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "keep-alive",
    "transfer-encoding",
    "trailer",
    "upgrade",
    "te",
}


def _serialize_request(request: HttpRequest, parsed: ParsedURL) -> bytes:
    lines = [
        f"{request.method.upper()} {parsed.request_target} HTTP/1.1".encode("ascii")
    ]
    has_host = any(
        name.decode("ascii").lower() == "host" for name, _ in request.headers
    )
    if not has_host:
        lines.append(f"Host: {parsed.http_authority}".encode("ascii"))
    for name, value in request.headers:
        lowered = name.decode("ascii").lower()
        if lowered in _HOP_BY_HOP or lowered == "proxy-credentials":
            continue
        lines.append(name + b": " + value)
    body = request.body or b""
    if body and not any(
        name.decode("ascii").lower() == "content-length" for name, _ in request.headers
    ):
        lines.append(f"Content-Length: {len(body)}".encode("ascii"))
    lines.append(b"Connection: close")
    head = b"\r\n".join(lines) + b"\r\n\r\n"
    return head + body


def _send_all(
    sock: Any, data: bytes, scope: OperationScope, limits: TransportLimits
) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(data):
        scope.remaining()
        chunk = view[offset : offset + limits.io_chunk_max]
        with contextlib.suppress(Exception):
            sock.setblocking(False)
        sel = selectors.DefaultSelector()
        try:
            sel.register(sock.fileno(), selectors.EVENT_WRITE)
        except Exception:
            sent = sock.send(memoryview(chunk))
            offset += sent
            continue
        try:
            left = scope.remaining()
            ready = sel.select(timeout=max(0.001, left))
            if not ready:
                raise DestinationDenied(
                    _deny("deadline_exceeded", "send timed out").refusal
                )
            sent = sock.send(memoryview(chunk))
        finally:
            sel.close()
        if sent <= 0:
            raise DestinationDenied(_deny("resolution_failed", "send failed").refusal)
        offset += sent


def _recv_chunk(
    sock: Any, scope: OperationScope, limits: TransportLimits, want: int
) -> bytes:
    scope.remaining()
    with contextlib.suppress(Exception):
        sock.setblocking(False)
    sel = selectors.DefaultSelector()
    try:
        sel.register(sock.fileno(), selectors.EVENT_READ)
    except Exception:
        buf = bytearray(min(want, limits.io_chunk_max))
        with memoryview(buf) as view:
            n = sock.recv_into(view)
        if n is None or n < 0:
            raise DestinationDenied(
                _deny("resolution_failed", "receive failed").refusal
            ) from None
        return bytes(buf[:n])
    try:
        left = scope.remaining()
        ready = sel.select(timeout=max(0.001, left))
        if not ready:
            raise DestinationDenied(
                _deny("deadline_exceeded", "receive timed out").refusal
            )
        buf = bytearray(min(want, limits.io_chunk_max))
        with memoryview(buf) as view:
            n = sock.recv_into(view)
        if n is None or n < 0:
            raise DestinationDenied(
                _deny("resolution_failed", "receive failed").refusal
            ) from None
        return bytes(buf[:n])
    finally:
        sel.close()


def _read_response(
    sock: Any,
    scope: OperationScope,
    limits: TransportLimits,
    sample_limit: int | None,
    method: str,
) -> tuple[
    int, bytes, HeaderPairs, bytes, bool, Literal["identity", "gzip", "deflate"]
]:
    cap = sample_limit if sample_limit is not None else limits.encoded_max
    buf = bytearray()
    interim = 0
    headers: HeaderPairs = ()
    status = 0
    reason = b""
    while True:
        chunk = _recv_chunk(sock, scope, limits, limits.io_chunk_max)
        if not chunk:
            raise DestinationDenied(
                _deny("response_framing", "incomplete response head").refusal
            )
        buf.extend(chunk)
        if len(buf) > limits.header_bytes_max + limits.header_line_max:
            raise DestinationDenied(
                _deny("over_bounds", "response head is oversized").refusal
            )
        idx = bytes(buf).find(b"\r\n\r\n")
        if idx >= 0:
            head = bytes(buf[:idx])
            rest = bytes(buf[idx + 4 :])
            break
    lines = head.split(b"\r\n")
    if not lines or len(lines[0]) > limits.header_line_max:
        raise DestinationDenied(_deny("response_framing", "bad status line").refusal)
    m = re.match(rb"^HTTP/1\.[01] (\d{3}) (.*)$", lines[0])
    if not m:
        raise DestinationDenied(_deny("response_framing", "bad status line").refusal)
    status = int(m.group(1))
    reason = m.group(2)
    raw_headers: list[tuple[bytes, bytes]] = []
    total = 0
    for line in lines[1:]:
        if len(line) > limits.header_line_max:
            raise DestinationDenied(
                _deny("over_bounds", "header line is oversized").refusal
            )
        if b":" not in line:
            raise DestinationDenied(
                _deny("response_framing", "bad header line").refusal
            )
        name, value = line.split(b":", 1)
        name = name.strip()
        value = value.strip()
        try:
            text = name.decode("ascii")
        except UnicodeDecodeError:
            raise DestinationDenied(
                _deny("response_framing", "header name must be ASCII").refusal
            ) from None
        if not _TOKEN_RE.match(text):
            raise DestinationDenied(
                _deny("response_framing", "header name is not a token").refusal
            )
        if b"\x00" in value or b"\r" in value or b"\n" in value:
            raise DestinationDenied(
                _deny("response_framing", "header value has bad bytes").refusal
            )
        total += len(name) + len(value)
        if (
            len(raw_headers) + 1 > limits.header_count_max
            or total > limits.header_bytes_max
        ):
            raise DestinationDenied(
                _deny("over_bounds", "too many response headers").refusal
            )
        raw_headers.append((name, value))
    lowered = [(n.decode("ascii").lower(), v) for n, v in raw_headers]
    while status in (100, 101, 102, 103):
        if status == 101:
            raise DestinationDenied(
                _deny("unsupported_channel", "protocol upgrade refused").refusal
            )
        interim += 1
        if interim > limits.interim_1xx_max:
            raise DestinationDenied(
                _deny("response_framing", "too many interim responses").refusal
            )
        raise DestinationDenied(
            _deny("response_framing", "interim response without final status").refusal
        )
    locations = [v for k, v in lowered if k == "location"]
    if len(set(locations)) > 1:
        raise DestinationDenied(
            _deny("response_framing", "incompatible Location headers").refusal
        )
    cls = [v for k, v in lowered if k == "content-length"]
    tes = [v for k, v in lowered if k == "transfer-encoding"]
    if len(set(cls)) > 1 or (cls and tes):
        raise DestinationDenied(_deny("response_framing", "ambiguous framing").refusal)
    if (
        any(
            b"upgrade" in v.lower() or b"connect" in v.lower()
            for k, v in lowered
            if k in ("upgrade", "connection")
        )
        and status == 101
    ):
        raise DestinationDenied(
            _deny("unsupported_channel", "protocol upgrade refused").refusal
        )
    encodings = [
        v.decode("latin1").strip().lower()
        for k, v in lowered
        if k == "content-encoding"
    ]
    if any(e not in ("identity", "gzip", "deflate", "") for e in encodings):
        raise DestinationDenied(
            _deny("unsupported_encoding", "unsupported content coding").refusal
        )
    encoding: Literal["identity", "gzip", "deflate"] = "identity"
    for e in encodings:
        if e in ("gzip", "deflate"):
            encoding = e  # type: ignore[assignment]
    bodyless = method == "HEAD" or status in (204, 304)
    if status == 204 and (cls or tes):
        raise DestinationDenied(
            _deny("response_framing", "204 must not carry framing").refusal
        )
    if bodyless:
        if rest:
            raise DestinationDenied(
                _deny("response_framing", "bodyless response has bytes").refusal
            )
        body, complete = b"", True
    else:
        is_chunked = any(b"chunked" in v.lower() for v in tes)
        if is_chunked:
            body, complete = _read_chunked(sock, rest, scope, limits, cap)
        elif cls:
            try:
                length = int(cls[0].decode("ascii").strip())
            except ValueError:
                raise DestinationDenied(
                    _deny("response_framing", "bad Content-Length").refusal
                ) from None
            if length < 0 or length > limits.encoded_max:
                raise DestinationDenied(
                    _deny("over_bounds", "Content-Length exceeds encoded_max").refusal
                )
            body, complete = _read_fixed(sock, rest, scope, limits, length, cap)
        else:
            body, complete = _read_until_close(sock, rest, scope, limits, cap)
    headers = tuple(raw_headers)
    return status, reason, headers, body, complete, encoding


def _read_fixed(
    sock: Any,
    rest: bytes,
    scope: OperationScope,
    limits: TransportLimits,
    length: int,
    cap: int,
) -> tuple[bytes, bool]:
    out = bytearray(rest[:length])
    while len(out) < length:
        chunk = _recv_chunk(sock, scope, limits, length - len(out))
        if not chunk:
            raise DestinationDenied(_deny("response_framing", "truncated body").refusal)
        out.extend(chunk)
        if len(out) > cap + 1:
            out = out[:cap]
            _drain_close(sock, scope, limits)
            return bytes(out), False
    if len(out) > cap:
        _drain_close(sock, scope, limits)
        return bytes(out[:cap]), False
    return bytes(out), True


def _read_chunked(
    sock: Any, rest: bytes, scope: OperationScope, limits: TransportLimits, cap: int
) -> tuple[bytes, bool]:
    buf = bytearray(rest)
    out = bytearray()
    complete = False
    while True:
        idx = bytes(buf).find(b"\r\n")
        while idx < 0:
            chunk = _recv_chunk(sock, scope, limits, limits.io_chunk_max)
            if not chunk:
                raise DestinationDenied(
                    _deny("response_framing", "truncated chunk").refusal
                )
            buf.extend(chunk)
            idx = bytes(buf).find(b"\r\n")
        line = bytes(buf[:idx]).split(b";", 1)[0].strip()
        del buf[: idx + 2]
        try:
            size = int(line.decode("ascii"), 16)
        except ValueError:
            raise DestinationDenied(
                _deny("response_framing", "bad chunk size").refusal
            ) from None
        if size < 0 or size > limits.encoded_max:
            raise DestinationDenied(
                _deny("over_bounds", "chunk exceeds encoded_max").refusal
            )
        if size == 0:
            while len(buf) < 2:
                chunk = _recv_chunk(sock, scope, limits, limits.io_chunk_max)
                if not chunk:
                    raise DestinationDenied(
                        _deny("response_framing", "truncated trailer").refusal
                    )
                buf.extend(chunk)
            complete = True
            break
        while len(buf) < size + 2:
            chunk = _recv_chunk(sock, scope, limits, limits.io_chunk_max)
            if not chunk:
                raise DestinationDenied(
                    _deny("response_framing", "truncated chunk body").refusal
                )
            buf.extend(chunk)
            if len(out) + len(buf) > limits.encoded_max + limits.io_chunk_max:
                raise DestinationDenied(
                    _deny("over_bounds", "chunked body is oversized").refusal
                )
        out.extend(buf[:size])
        del buf[: size + 2]
        if len(out) > cap:
            _drain_close(sock, scope, limits)
            return bytes(out[:cap]), False
    if len(out) > cap:
        return bytes(out[:cap]), False
    return bytes(out), complete


def _read_until_close(
    sock: Any, rest: bytes, scope: OperationScope, limits: TransportLimits, cap: int
) -> tuple[bytes, bool]:
    out = bytearray(rest)
    if len(out) > cap:
        _drain_close(sock, scope, limits)
        return bytes(out[:cap]), False
    while True:
        chunk = _recv_chunk(sock, scope, limits, limits.io_chunk_max)
        if not chunk:
            break
        out.extend(chunk)
        if len(out) > cap:
            _drain_close(sock, scope, limits)
            return bytes(out[:cap]), False
        if len(out) > limits.encoded_max:
            raise DestinationDenied(
                _deny("over_bounds", "body exceeds encoded_max").refusal
            )
    return bytes(out), True


def _drain_close(sock: Any, scope: OperationScope, limits: TransportLimits) -> None:
    with contextlib.suppress(Exception):
        sock.setblocking(False)
    with contextlib.suppress(Exception):
        sock.shutdown(socket.SHUT_RD)


def _decode_body(
    response: SafeResponse,
    request: HttpRequest,
    decoded_max: int,
    limits: TransportLimits,
) -> tuple[Literal["entity", "head", "no_content", "not_modified"], bytes]:
    method = request.method.upper()
    if method == "HEAD":
        if response.body:
            raise DestinationDenied(_deny("response_framing", "HEAD has bytes").refusal)
        return "head", b""
    if response.status == 304:
        if response.body:
            raise DestinationDenied(_deny("response_framing", "304 has bytes").refusal)
        return "not_modified", b""
    if response.status == 204:
        if response.body:
            raise DestinationDenied(_deny("response_framing", "204 has bytes").refusal)
        return "no_content", b""
    data = response.body
    if response.content_encoding == "identity":
        decoded = data
    elif response.content_encoding == "gzip":
        try:
            decoded = gzip.decompress(data)
        except Exception:
            raise DestinationDenied(
                _deny("response_framing", "gzip trailer is invalid").refusal
            ) from None
    else:
        try:
            decoded = zlib.decompress(data, wbits=zlib.MAX_WBITS)
        except Exception:
            try:
                decoded = zlib.decompress(data, wbits=-zlib.MAX_WBITS)
            except Exception:
                raise DestinationDenied(
                    _deny("response_framing", "deflate stream is invalid").refusal
                ) from None
    if len(decoded) > decoded_max:
        raise DestinationDenied(
            _deny("over_bounds", "decoded output exceeds decoded_max").refusal
        )
    if len(data) > 0 and len(decoded) > len(data) * limits.ratio_max + 1024:
        raise DestinationDenied(
            _deny("over_bounds", "decode ratio exceeds ratio_max").refusal
        )
    return "entity", decoded


def _decoded_headers(
    headers: HeaderPairs,
    status: int,
    method: str,
    kind: Literal["entity", "head", "no_content", "not_modified"],
    decoded_len: int,
) -> HeaderPairs:
    out: list[tuple[bytes, bytes]] = []
    connection_names: set[bytes] = set()
    for name, value in headers:
        lowered = name.decode("ascii").lower()
        if lowered == "connection":
            for part in value.split(b","):
                connection_names.add(part.strip().lower())
    for name, value in headers:
        lowered = name.decode("ascii").lower()
        if lowered in _HOP_BY_HOP or lowered in ("content-encoding",):
            continue
        if name.lower() in connection_names:
            continue
        if kind == "entity" and lowered == "content-length":
            continue
        out.append((name, value))
    if kind == "entity":
        out.append((b"Content-Length", str(decoded_len).encode("ascii")))
    return tuple(out)


class SafeFetch:
    def __init__(self, transport: DestinationTransport) -> None:
        self._transport = transport

    @property
    def authority(self) -> AuthorityHandle:
        return self._transport.authority

    @property
    def transport(self) -> DestinationTransport:
        return self._transport

    def __call__(
        self, url: str, timeout: float = 15.0, *, operation: RootOperation
    ) -> dict[str, object]:
        transport = self._transport
        if operation.authority is not transport.authority:
            return {"error": "not_configured: foreign operation authority"}
        with transport._lock:
            if id(operation.identity._token) not in transport._roots:
                return {"error": "not_configured: unknown operation"}
            if id(operation.identity._token) in transport._root_finished:
                return {"error": "upstream_error: operation is finished"}
        try:
            operation.remaining()
        except DestinationDenied as exc:
            return {"error": f"{exc.refusal.public_code}: {exc.refusal.message}"}
        cap = min(timeout, 15.0)
        deadline = min(operation.deadline_at, transport._clock.monotonic() + cap)
        scope = transport.open_scope(operation=operation, deadline_at=deadline)
        try:
            request = HttpRequest(
                url=url,
                method="GET",
                headers=(
                    (b"User-Agent", b"omega-prime/preview-check"),
                    (b"Accept-Encoding", b"identity"),
                    (b"Accept", b"*/*"),
                ),
                body=None,
            )
            try:
                response = transport.fetch(
                    request,
                    scope=scope,
                    sample_limit=transport.limits.preview_sample_max,
                )
            except DestinationDenied as exc:
                return {"error": f"{exc.refusal.public_code}: {exc.refusal.message}"}
            lowered: dict[str, str] = {}
            for name, value in response.headers:
                try:
                    lowered[name.decode("latin1").lower()] = value.decode("latin1")
                except Exception:
                    continue
            return {
                "status": response.status,
                "headers": lowered,
                "body": response.body,
                "ms": round(response.elapsed_ms, 1),
            }
        finally:
            scope.close()


__all__ = [
    "AbortHandle",
    "AbortSubscription",
    "AuthorityHandle",
    "ConnectionIdentity",
    "DecodeBudget",
    "DecodedResponse",
    "DestinationDenied",
    "DestinationPermit",
    "DestinationTransport",
    "HeaderPairs",
    "HttpRequest",
    "NumericDialer",
    "OperationBinding",
    "OperationDrain",
    "OperationIdentity",
    "OperationScope",
    "ParsedURL",
    "PublicCode",
    "Reason",
    "Refusal",
    "ResolvedAddress",
    "Resolver",
    "RootOperation",
    "SafeFetch",
    "SafeResponse",
    "ScopeIdentity",
    "TLSVerifier",
    "TransportLimits",
    "ValidatedConnection",
    "parse_url",
]
