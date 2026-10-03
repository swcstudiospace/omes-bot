"""Minimal DAP client: launch, break, stop, inspect, disconnect.

Ports the ``packages/coding-agent/src/dap`` session flow over an
:class:`omes.tools.rpc.RpcConnection`: ``initialize`` plus the
``initialized`` event, ``launch``, ``setBreakpoints``,
``configurationDone``, the ``stopped`` event, ``threads`` and
``stackTrace``, then ``disconnect``. Requests carry ``seq`` numbers and
responses are matched by ``request_seq``; events stash in arrival order.
No attach, no restart, no variable inspection.
"""

from __future__ import annotations

from typing import Any

from omes.tools.rpc import RpcConnection


class DapError(RuntimeError):
    """The adapter answered ``success: false`` or skipped the handshake."""


class DapSession:
    """One adapter, one launch. Use as a context manager."""

    def __init__(self, connection: RpcConnection) -> None:
        self._connection = connection
        self._seq = 0
        self._events: list[dict] = []
        self._started = False

    def __enter__(self) -> DapSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        self._connection.close()

    @property
    def connection(self) -> RpcConnection:
        return self._connection

    def start(self, timeout: float | None = None) -> dict:
        """Run ``initialize`` and wait for the ``initialized`` event."""
        body = self._request(
            "initialize",
            {"adapterID": "omes", "pathFormat": "path"},
            timeout=timeout,
        )
        self._await_event("initialized", timeout=timeout)
        self._started = True
        return body if isinstance(body, dict) else {}

    def launch(
        self, program: str, extra: dict | None = None, timeout: float | None = None
    ) -> None:
        """Launch ``program``. Require a successful response."""
        self._require_started()
        arguments: dict[str, Any] = {"program": program}
        if extra:
            arguments.update(extra)
        self._request("launch", arguments, timeout=timeout)

    def set_breakpoints(
        self, path: str, lines: list[int], timeout: float | None = None
    ) -> list:
        """Set one breakpoint per line. Return the verified breakpoints."""
        self._require_started()
        body = self._request(
            "setBreakpoints",
            {
                "source": {"path": path},
                "breakpoints": [{"line": line} for line in lines],
            },
            timeout=timeout,
        )
        if not isinstance(body, dict):
            return []
        found = body.get("breakpoints", [])
        return list(found) if isinstance(found, list) else []

    def configuration_done(self, timeout: float | None = None) -> None:
        """Send ``configurationDone``. Require a successful response."""
        self._require_started()
        self._request("configurationDone", None, timeout=timeout)

    def wait_stopped(self, timeout: float | None = None) -> dict:
        """Return the first ``stopped`` event body."""
        self._require_started()
        return self._await_event("stopped", timeout=timeout)

    def threads(self, timeout: float | None = None) -> list:
        """Return the adapter's thread list."""
        self._require_started()
        body = self._request("threads", None, timeout=timeout)
        if not isinstance(body, dict):
            return []
        found = body.get("threads", [])
        return list(found) if isinstance(found, list) else []

    def stack_trace(
        self, thread_id: int, timeout: float | None = None
    ) -> list:
        """Return the stack frames for ``thread_id``."""
        self._require_started()
        body = self._request("stackTrace", {"threadId": thread_id}, timeout=timeout)
        if not isinstance(body, dict):
            return []
        found = body.get("stackFrames", [])
        return list(found) if isinstance(found, list) else []

    def disconnect(self, timeout: float | None = None) -> None:
        """Send ``disconnect`` and close the connection. Idempotent."""
        if not self._started:
            self._connection.close()
            return
        self._started = False
        try:
            self._request("disconnect", {"terminateDebuggee": True}, timeout=timeout)
        finally:
            self._connection.close()

    def _require_started(self) -> None:
        if not self._started:
            raise DapError("session is not started")

    def _request(
        self, command: str, arguments: Any, timeout: float | None
    ) -> Any:
        self._seq += 1
        request_seq = self._seq
        message: dict[str, Any] = {
            "seq": request_seq,
            "type": "request",
            "command": command,
        }
        if arguments is not None:
            message["arguments"] = arguments
        self._connection.send(message)
        while True:
            inbound = self._connection.read_message(timeout=timeout)
            if not isinstance(inbound, dict):
                continue
            if inbound.get("type") == "event":
                self._events.append(inbound)
                continue
            if (
                inbound.get("type") == "response"
                and inbound.get("request_seq") == request_seq
            ):
                if inbound.get("success") is not True:
                    raise DapError(f"{command} failed: {inbound.get('message')}")
                return inbound.get("body")
            continue

    def _await_event(self, name: str, timeout: float | None) -> dict:
        for index, stashed in enumerate(self._events):
            if stashed.get("event") == name:
                return self._events.pop(index).get("body") or {}
        while True:
            inbound = self._connection.read_message(timeout=timeout)
            if not isinstance(inbound, dict):
                continue
            if inbound.get("type") != "event":
                continue
            if inbound.get("event") == name:
                body = inbound.get("body")
                return body if isinstance(body, dict) else {}
            self._events.append(inbound)


__all__ = ["DapError", "DapSession"]
