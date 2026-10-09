# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Request correlation and structured logging for the Grok Bot host.

* W3C Trace Context: `TraceContext`, strict `parse_traceparent`, `new_trace_context`,
  `format_traceparent`.
* `RequestContextMiddleware` gives every HTTP request a request id and a trace context
  (`scope["state"]["request_id"]` / `["trace"]`, plus a `request_id_var` context
  variable for log records) and echoes them as response headers.
* `JsonLogFormatter` / `configure_logging`: NDJSON logs with credentials redacted.
* `AccessLogMiddleware`: one access record per request that never carries a query
  string, a header value or a body.

All middleware is pure ASGI so streaming (SSE) responses are never buffered.
"""

from __future__ import annotations

import json
import logging
import math
import re
import secrets
import sys
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from omega_prime.grokbot.audit import redact_sensitive, sanitize_payload
from omega_prime.grokbot.security import principal_from_scope

ACCESS_LOGGER_NAME = "omega_prime.access"
ROOT_LOGGER_NAME = "omega_prime"
REQUEST_ID_HEADER = b"x-request-id"
TRACEPARENT_HEADER = b"traceparent"

request_id_var: ContextVar[str | None] = ContextVar("omega_request_id", default=None)

_TRACEPARENT = re.compile(
    r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})",
    re.IGNORECASE | re.ASCII,
)
_ZERO_TRACE = "0" * 32
_ZERO_SPAN = "0" * 16
_DEFAULT_FLAGS = "01"
_MAX_PATH_CHARS = 512
_MAX_JSON_DEPTH = 4
_HANDLER_NAME = "omega_prime.grokbot.telemetry"
_TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


# ----------------------------------------------------------------------- trace context


@dataclass(frozen=True)
class TraceContext:
    """A W3C trace context position: lowercase hex ids and trace flags."""

    trace_id: str
    span_id: str
    flags: str = _DEFAULT_FLAGS
    parent_span_id: str | None = None


def parse_traceparent(value: object) -> TraceContext | None:
    """Parse `00-<32hex>-<16hex>-<2hex>`; None for anything else.

    Strict: version `00` only, all-zero trace or span ids are invalid, no surrounding
    whitespace. Hex is case-insensitive and normalized to lowercase.
    """
    if not isinstance(value, str):
        return None
    match = _TRACEPARENT.fullmatch(value)
    if match is None:
        return None
    version, trace_id, span_id, flags = (part.lower() for part in match.groups())
    if version != "00" or trace_id == _ZERO_TRACE or span_id == _ZERO_SPAN:
        return None
    return TraceContext(trace_id=trace_id, span_id=span_id, flags=flags)


def _random_hex(nbytes: int) -> str:
    value = secrets.token_hex(nbytes)
    while not value.strip("0"):  # all-zero ids are invalid
        value = secrets.token_hex(nbytes)
    return value


def new_trace_context(parent: TraceContext | None = None) -> TraceContext:
    """A fresh span; with a `parent` it keeps the trace id and flags."""
    if parent is None:
        return TraceContext(_random_hex(16), _random_hex(8), _DEFAULT_FLAGS, None)
    return TraceContext(parent.trace_id, _random_hex(8), parent.flags, parent.span_id)


def format_traceparent(ctx: TraceContext) -> str:
    """The `traceparent` header value for `ctx`."""
    return f"00-{ctx.trace_id}-{ctx.span_id}-{ctx.flags}"


# ---------------------------------------------------------------------------- ASGI


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key.lower() == name:
            return bytes(value).decode("latin-1")
    return None


class RequestContextMiddleware:
    """Mint a request id and trace context for every HTTP request.

    An inbound `traceparent` that parses is continued with a fresh span; a malformed
    one is replaced and never echoed. An inbound `X-Request-Id` is ignored: ids are
    minted here (the first 16 hex characters of the trace id) so a client cannot
    forge an arbitrary id into logs and audit records.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ctx = new_trace_context(parse_traceparent(_header(scope, TRACEPARENT_HEADER)))
        request_id = ctx.trace_id[:16]
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["trace"] = ctx
        added = [
            (REQUEST_ID_HEADER, request_id.encode("ascii")),
            (TRACEPARENT_HEADER, format_traceparent(ctx).encode("ascii")),
        ]

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", ())
                    if key.lower() not in (REQUEST_ID_HEADER, TRACEPARENT_HEADER)
                ]
                message = {**message, "headers": [*headers, *added]}
            await send(message)

        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)


def _printable(text: str) -> str:
    """Neutralize control characters (log injection) and bound the length."""
    safe = "".join(
        ch if ch.isprintable() else f"\\x{ord(ch):02x}" for ch in text[:_MAX_PATH_CHARS]
    )
    return redact_sensitive(safe)


class AccessLogMiddleware:
    """One `omega_prime.access` record per HTTP request, after it ends.

    Logged: method, path WITHOUT its query string, status, duration, principal id and
    request id. Never logged: query string, any header value, request or response
    body. Place it inside `RequestContextMiddleware` (for the request id); it sees the
    principal when it wraps or sits beside authentication through the shared scope
    state.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.app = app
        self.logger = logger or logging.getLogger(ACCESS_LOGGER_NAME)
        self._clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        started = self._clock()
        status = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException:
            if status == 0:
                status = 500
            raise
        finally:
            self._emit(scope, state, status, (self._clock() - started) * 1000.0)

    def _emit(self, scope: Scope, state: Any, status: int, duration_ms: float) -> None:
        principal = principal_from_scope(scope)
        request_id = state.get("request_id") if hasattr(state, "get") else None
        method = _printable(str(scope.get("method", "")))
        path = _printable(str(scope.get("path", "")))
        principal_id = principal.id if principal is not None else None
        duration = round(max(0.0, duration_ms), 3)
        self.logger.info(
            "%s %s %d %.1fms principal=%s request_id=%s",
            method,
            path,
            status,
            duration,
            principal_id or "-",
            request_id or "-",
            extra={
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": duration,
                "principal": principal_id,
                "request_id": request_id if isinstance(request_id, str) else None,
            },
        )


# ---------------------------------------------------------------------------- logging

_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
    # uvicorn adds an ANSI-coloured copy of `msg`; it is noise in structured logs.
    "color_message",
}
_RESERVED_KEYS = frozenset({"ts", "level", "logger", "msg", "exc", "stack"})
_UNSAFE = object()


def _json_safe(value: Any, depth: int = 0) -> Any:
    """`value` when it is plain JSON data, else the `_UNSAFE` sentinel."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if depth >= _MAX_JSON_DEPTH:
        return _UNSAFE
    if isinstance(value, (list, tuple)):
        items = [_json_safe(item, depth + 1) for item in value]
        return _UNSAFE if any(item is _UNSAFE for item in items) else items
    if isinstance(value, dict):
        converted: dict[str, Any] = {}
        for key, item in value.items():
            safe = _json_safe(item, depth + 1)
            if not isinstance(key, str) or safe is _UNSAFE:
                return _UNSAFE
            converted[key] = safe
        return converted
    return _UNSAFE


class JsonLogFormatter(logging.Formatter):
    """One JSON object per record; every string is credential-redacted.

    Fields: `ts` (ISO-8601 UTC), `level`, `logger`, `msg`, `request_id` (from the
    record's `extra`, else `request_id_var`), `exc` for exceptions, plus any
    JSON-safe `extra` fields (sensitive-looking keys are masked). Output is ASCII-only
    so a line separator can never split a record.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact_sensitive(record.getMessage()),
        }
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key in _RESERVED_KEYS or key.startswith("_"):
                continue
            safe = _json_safe(value)
            if safe is not _UNSAFE:
                extras[key] = safe
        entry.update(sanitize_payload(extras))
        request_id = entry.get("request_id") or request_id_var.get()
        if request_id:
            entry["request_id"] = redact_sensitive(str(request_id))
        else:
            entry.pop("request_id", None)
        if record.exc_info:
            entry["exc"] = redact_sensitive(self.formatException(record.exc_info))
        if record.stack_info:
            entry["stack"] = redact_sensitive(self.formatStack(record.stack_info))
        return json.dumps(entry, separators=(",", ":"), default=str)


class _RedactingTextFormatter(logging.Formatter):
    """The plain text format, with credentials redacted from the whole line."""

    def format(self, record: logging.LogRecord) -> str:
        return redact_sensitive(super().format(record))


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    resolved = logging.getLevelNamesMapping().get(level.strip().upper())
    if resolved is None:
        raise ValueError(f"unknown log level: {level!r}")
    return resolved


def configure_logging(fmt: str = "text", level: str | int = "INFO") -> None:
    """Configure the `omega_prime` logger tree (idempotent).

    Installs exactly one stderr stream handler on the `omega_prime` logger, with
    `JsonLogFormatter` for `fmt="json"` or a redacting plain formatter for `"text"`.
    Calling again reconfigures that handler instead of adding another. The root
    logger and its handlers are never touched; `omega_prime` stops propagating so
    records are not emitted twice when the host application configures the root.
    """
    if fmt not in ("text", "json"):
        raise ValueError(f"log format must be 'text' or 'json', not {fmt!r}")
    resolved = _resolve_level(level)
    formatter: logging.Formatter = (
        JsonLogFormatter() if fmt == "json" else _RedactingTextFormatter(_TEXT_FORMAT)
    )
    target = logging.getLogger(ROOT_LOGGER_NAME)
    handler = next((h for h in target.handlers if h.get_name() == _HANDLER_NAME), None)
    if handler is None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.set_name(_HANDLER_NAME)
        target.addHandler(stream_handler)
        handler = stream_handler
    elif (
        isinstance(handler, logging.StreamHandler) and handler.stream is not sys.stderr
    ):
        handler.setStream(sys.stderr)
    handler.setFormatter(formatter)
    target.setLevel(resolved)
    target.propagate = False


__all__ = [
    "ACCESS_LOGGER_NAME",
    "AccessLogMiddleware",
    "JsonLogFormatter",
    "RequestContextMiddleware",
    "TraceContext",
    "configure_logging",
    "format_traceparent",
    "new_trace_context",
    "parse_traceparent",
    "request_id_var",
]
