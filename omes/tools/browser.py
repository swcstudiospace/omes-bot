"""Direct browser session through the guarded factory.

BrowserSession publishes only from its own registered clean terminal
receipt; follow-up snapshots use the immutable finalized cache.
"""

from __future__ import annotations

import time
from typing import Any


class BrowserSession:
    """Direct caller restricted to registered factory ownership."""

    def __init__(self, factory: Any | None) -> None:
        self._factory = factory
        self._cached: dict[str, Any] | None = None

    def _resolve_operation(self, operation: Any | None) -> Any:
        if operation is not None:
            return operation
        if self._factory is None:
            return None
        transport = self._factory.transport
        current = getattr(transport, "current_operation", None)
        if callable(current):
            bound = current()
            if bound is not None:
                return bound
        now = time.time()
        return transport.begin_operation(deadline_at=now + 60.0)

    def browser_navigate(
        self, url: str, *, operation: Any | None = None
    ) -> dict[str, Any]:
        self._cached = None
        if self._factory is None:
            return {"error": "browser transport is not available"}
        if not isinstance(url, str) or url.strip() == "":
            return {"error": "url must be a non-empty string"}
        root = self._resolve_operation(operation)
        if root is None:
            return {"error": "browser transport is not available"}
        transport = self._factory.transport
        session = self._factory.create_session(operation=root)
        try:
            started = session.start()
            if "error" in started:
                return {"error": started["error"]}
            navigated = session.navigate(url)
            if "error" in navigated:
                return {"error": navigated["error"]}
            snap = session.snapshot()
            if "error" in snap:
                return {"error": snap["error"]}
        finally:
            close_outcome = session.close()
        receipt = session.receipt
        if not close_outcome.get("ok", False):
            return {"error": "browser close failed", "close": close_outcome}
        if receipt is None or not self._factory.owns(session, receipt):
            return {"error": "foreign browser receipt"}
        if not receipt.clean:
            return {"error": "browser session was not clean", "close": close_outcome}
        try:
            drain = transport.finish_operation(root, deadline_at=root.deadline_at)
        except Exception as exc:
            return {"error": f"operation drain failed: {exc}"}
        if not getattr(drain, "complete", False) or bool(
            getattr(drain, "pending_scopes", 0)
        ):
            return {"error": "operation drain incomplete"}
        if getattr(drain, "errors", ()):
            return {"error": "operation drain failed"}
        if getattr(root.abort_handle, "reason", None) is not None:
            return {"error": "operation aborted"}
        page = {"title": navigated["title"], "url": navigated["url"]}
        self._cached = {
            "factory": self._factory,
            "session_identity": session.session_identity,
            "receipt": receipt,
            "root": root,
            "drain": drain,
            "page": page,
        }
        return {"url": url, "page": page}

    def browser_snapshot(self, *, operation: Any | None = None) -> dict[str, Any]:
        if self._cached is None:
            return {"error": "no completed navigation"}
        cached = self._cached
        factory = cached["factory"]
        receipt = cached["receipt"]
        historical = cached["root"]
        if factory is not self._factory:
            return {"error": "foreign browser receipt"}
        if receipt is None or not receipt.clean:
            return {"error": "browser session was not clean"}
        if getattr(historical.abort_handle, "reason", None) is not None:
            return {"error": "historical operation aborted"}
        transport = self._factory.transport if self._factory is not None else None
        if transport is None:
            return {"error": "browser transport is not available"}
        current = operation
        if current is None:
            getter = getattr(transport, "current_operation", None)
            if callable(getter):
                current = getter()
        if current is None:
            now = time.time()
            current = transport.begin_operation(deadline_at=now + 15.0)
        try:
            deadline = getattr(current, "deadline_at", time.time() + 15.0)
            drain = transport.finish_operation(current, deadline_at=deadline)
        except Exception as exc:
            return {"error": f"snapshot drain failed: {exc}"}
        if not getattr(drain, "complete", False):
            return {"error": "snapshot drain incomplete"}
        abort_handle = getattr(current, "abort_handle", None)
        if getattr(abort_handle, "reason", None) is not None:
            return {"error": "snapshot operation aborted"}
        return {"page": dict(cached["page"])}


__all__ = ["BrowserSession"]
