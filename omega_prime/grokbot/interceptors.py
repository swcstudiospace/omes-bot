# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tool-call interceptors: policy around dispatch, composed rather than hard-coded.

An interceptor sees every `tools/call` before dispatch (`before`, which may deny)
and after it (`after`, observation only). Scope checks, audit records and in-flight
accounting are interceptors; later layers (rate limits, breakers, metrics) join the
same chain without editing the MCP handler.

Chain semantics (`run_tool_call`):
- interceptors run in order; the first denial stops the chain and the tool is NOT
  dispatched;
- `after` runs for every interceptor whose `before` ran, including the one that
  denied and those before it, so counters stay balanced;
- an exception in `before` is a denial with code `interceptor_error` (fail closed);
- an exception in `after` is logged by type and swallowed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from omega_prime.grokbot.audit import sanitize_payload
from omega_prime.grokbot.security import (
    SCOPE_CALL,
    Principal,
    principal_from_request,
)

logger = logging.getLogger(__name__)

_ERROR_PREVIEW_CHARS = 200
_ARGS_MODES = ("digest", "redacted")


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    principal: Principal | None
    transport: str = "stdio"
    request_id: str | None = None


@dataclass(frozen=True)
class ToolDenial:
    code: str
    message: str
    retry_after: float | None = None


@dataclass(frozen=True)
class ToolOutcome:
    status: str
    is_error: bool
    duration_ms: float
    error: str | None = None
    denial_code: str | None = None


class ToolCallInterceptor(Protocol):
    def before(self, call: ToolCall) -> ToolDenial | None: ...

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None: ...


def call_from_context(
    ctx: Any, name: str, arguments: Any, *, transport: str = "stdio"
) -> ToolCall:
    """Build a `ToolCall` from the MCP request context.

    `ctx.request` is the Starlette request on HTTP transports and None on stdio
    (no principal: the caller is the local operator).
    """
    request = getattr(ctx, "request", None)
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    return ToolCall(
        name=name,
        arguments=dict(arguments) if isinstance(arguments, dict) else {},
        principal=principal_from_request(request),
        transport=transport,
        request_id=request_id if isinstance(request_id, str) else None,
    )


def _payload_error(payload: str) -> tuple[bool, str | None]:
    """Whether a result payload is an error, by the MCP handler's rule."""
    try:
        decoded = json.loads(payload)
    except ValueError:
        return False, None
    if isinstance(decoded, dict) and decoded.get("error") is not None:
        return True, str(decoded["error"])
    return False, None


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _run_after(
    ran: Sequence[ToolCallInterceptor], call: ToolCall, outcome: ToolOutcome
) -> None:
    for interceptor in ran:
        try:
            interceptor.after(call, outcome)
        except Exception as exc:
            logger.warning(
                "interceptor %s.after raised %s",
                type(interceptor).__name__,
                type(exc).__name__,
            )


def run_tool_call(
    interceptors: Sequence[ToolCallInterceptor],
    call: ToolCall,
    dispatch: Callable[[], str],
) -> tuple[str, ToolOutcome]:
    """Run `dispatch` through the interceptor chain.

    Returns the result payload (JSON text) and the outcome. A denial yields
    `{"error": "<code>: <message>", "tool": <name>}`. An exception raised by
    `dispatch` itself propagates after `after` hooks have observed it.
    """
    started = time.perf_counter()
    ran: list[ToolCallInterceptor] = []
    denial: ToolDenial | None = None
    for interceptor in interceptors:
        ran.append(interceptor)
        try:
            denial = interceptor.before(call)
        except Exception as exc:
            logger.warning(
                "interceptor %s.before raised %s",
                type(interceptor).__name__,
                type(exc).__name__,
            )
            denial = ToolDenial(
                "interceptor_error", f"{type(interceptor).__name__} failed"
            )
        if denial is not None:
            break
    if denial is not None:
        payload = json.dumps(
            {"error": f"{denial.code}: {denial.message}", "tool": call.name}
        )
        outcome = ToolOutcome(
            status="denied",
            is_error=True,
            duration_ms=_elapsed_ms(started),
            error=f"{denial.code}: {denial.message}",
            denial_code=denial.code,
        )
        _run_after(ran, call, outcome)
        return payload, outcome
    try:
        payload = dispatch()
    except Exception as exc:
        _run_after(
            ran,
            call,
            ToolOutcome(
                status="error",
                is_error=True,
                duration_ms=_elapsed_ms(started),
                error=f"{type(exc).__name__}: {exc}",
            ),
        )
        raise
    is_error, error = _payload_error(payload)
    outcome = ToolOutcome(
        status="error" if is_error else "ok",
        is_error=is_error,
        duration_ms=_elapsed_ms(started),
        error=error,
    )
    _run_after(ran, call, outcome)
    return payload, outcome


class ScopeInterceptor:
    """Deny callers whose principal lacks the `call` scope.

    No principal (stdio, or a no-auth loopback host) means the local operator.
    """

    def before(self, call: ToolCall) -> ToolDenial | None:
        principal = call.principal
        if principal is None or principal.allows(SCOPE_CALL):
            return None
        return ToolDenial(
            "forbidden", f"principal {principal.id} lacks the {SCOPE_CALL} scope"
        )

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call, outcome


class _AuditSink(Protocol):
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
    ) -> Any: ...


class AuditInterceptor:
    """Record one `tool_call` audit event per call.

    By default only argument key names and a SHA-256 digest of the canonical
    arguments are stored, never values. `args_mode="redacted"` additionally stores
    the credential-scrubbed arguments.
    """

    def __init__(self, tracer: _AuditSink, *, args_mode: str = "digest") -> None:
        if args_mode not in _ARGS_MODES:
            raise ValueError(f"args_mode must be one of {', '.join(_ARGS_MODES)}")
        self._tracer = tracer
        self._args_mode = args_mode

    def before(self, call: ToolCall) -> ToolDenial | None:
        del call
        return None

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        canonical = json.dumps(
            call.arguments,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        details: dict[str, Any] = {
            "arg_keys": sorted(str(key) for key in call.arguments),
            "args_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "transport": call.transport,
            "request_id": call.request_id,
            "denial": outcome.denial_code,
            "error": (
                str(sanitize_payload(outcome.error))[:_ERROR_PREVIEW_CHARS]
                if outcome.error is not None
                else None
            ),
        }
        if self._args_mode == "redacted":
            details["arguments"] = sanitize_payload(call.arguments)
        self._tracer.log_event(
            "tool_call",
            tool_name=call.name,
            caller=call.principal.id if call.principal else "local",
            status=outcome.status,
            duration_ms=outcome.duration_ms,
            is_error=outcome.is_error,
            details=details,
        )


class InFlightInterceptor:
    """Counts calls between `before` and `after` (for graceful drain)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def before(self, call: ToolCall) -> ToolDenial | None:
        del call
        with self._lock:
            self._count += 1
        return None

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call, outcome
        with self._lock:
            self._count -= 1


__all__ = [
    "AuditInterceptor",
    "InFlightInterceptor",
    "ScopeInterceptor",
    "ToolCall",
    "ToolCallInterceptor",
    "ToolDenial",
    "ToolOutcome",
    "call_from_context",
    "run_tool_call",
]
