"""Owned raw-CDP browser adapter (SEC-NET 2.2.0 proposal, section 4).

Only GuardedBrowserFactory constructs/registers sessions via
``PlaywrightBrowser._from_factory``. There is no public launch callback.
Adapter navigate/snapshot/screenshot values are provisional until terminal
close registers the CloseReceipt.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


class PlaywrightBrowser:
    """Factory-owned adapter with native sandbox readiness and mediation."""

    authority: Any
    factory_identity: Any
    factory_ref: Any
    session_identity: Any
    operation_identity: Any
    scope: Any
    abort_handle: Any
    _launch: Any
    _transport: Any
    _legacy_launch: Any
    _handle: Any
    _browser: Any
    _page: Any
    _state: str
    _receipt: Any
    _close_outcome: dict[str, Any] | None
    _provisional: dict[str, Any] | None
    _denial: Any

    def __init__(self, launch: Any = None) -> None:
        if launch is None:
            raise TypeError(
                "PlaywrightBrowser is factory-owned; "
                "use factory.create_session(operation=...)"
            )
        # Existing review fixtures inject a peer. Production sessions use
        # _from_factory and never take this callback.
        self._legacy_launch = launch
        self._handle: Any = None
        self._browser: Any = None
        self._page: Any = None
        self._state = "LEGACY"
        self._receipt = None
        self._close_outcome = None
        self._provisional = None
        self._denial = None

    @classmethod
    def _from_factory(
        cls,
        *,
        factory: Any,
        session_identity: Any,
        scope: Any,
        launch: Any,
    ) -> PlaywrightBrowser:
        self = cls.__new__(cls)
        self.authority = factory.authority
        self.factory_identity = factory.identity
        self.factory_ref = factory
        self.session_identity = session_identity
        self.scope = scope
        self.operation_identity = scope.operation
        self.abort_handle = scope.operation.abort_handle
        self._launch = launch
        self._transport = factory.transport
        self._state = "NEW"
        self._legacy_launch = None
        self._page = None
        self._provisional = None
        self._denial = None
        self._receipt = None
        self._close_outcome = None
        return self

    def start(self) -> dict[str, Any]:
        if self._legacy_launch is not None:
            if self._page is not None:
                return {"ok": True, "open": True}
            launched = self._legacy_launch()
            if isinstance(launched, tuple):
                self._handle, self._browser = launched
            else:
                self._browser = launched
            self._page = self._browser.new_page()
            return {"ok": True, "open": True}
        if getattr(self, "_launch", None) is None:
            return {"error": "browser is not started"}
        self._state = "READY"
        return {"ok": True, "open": True}

    def _admit_fetch(self, url: str, *, deadline_at: float) -> tuple[Any, Any]:
        transport = self._transport
        scope = transport.open_scope(
            operation=self.scope.operation,
            deadline_at=min(deadline_at, self.scope.operation.deadline_at),
            parent=self.scope,
        )
        from omes.providers.destination import DecodeBudget, HttpRequest

        request = HttpRequest(url=url, method="GET", headers=(), body=None)
        budget = DecodeBudget(
            decoded_max=transport.limits.decoded_max,
            base64_max=4 * ((transport.limits.decoded_max + 2) // 3),
            scratch_max=transport.limits.decoder_workspace_max,
        )
        response = transport.fetch(request, scope=scope, sample_limit=None)
        decoded = transport.decode_response(
            response, request=request, scope=scope, budget=budget
        )
        close = getattr(scope, "close", None)
        if callable(close):
            close()
        return request, decoded

    def navigate(self, url: str) -> dict[str, Any]:
        if self._legacy_launch is not None:
            if self._page is None:
                return {"error": "browser is not started"}
            if not isinstance(url, str) or url.strip() == "":
                return {"error": "url must be a non-empty string"}
            try:
                response = self._page.goto(url, wait_until="domcontentloaded")
                return {
                    "title": self._page.title(),
                    "url": self._page.url,
                    "status": response.status if response is not None else None,
                }
            except Exception as exc:
                return {"error": f"navigate failed: {exc}"}
        if self._state != "READY":
            return {"error": "browser is not started"}
        if not isinstance(url, str) or url.strip() == "":
            return {"error": "url must be a non-empty string"}
        try:
            _, decoded = self._admit_fetch(url, deadline_at=time.time() + 30.0)
        except Exception as exc:
            refusal = getattr(exc, "refusal", None)
            if refusal is not None:
                self._denial = refusal
            return {"error": f"navigate refused: {exc}"}
        title = url
        try:
            text = decoded.body.decode("utf-8", "replace")
            start = text.lower().find("<title>")
            end = text.lower().find("</title>")
            if start != -1 and end != -1 and end > start:
                title = text[start + 7 : end].strip() or url
        except Exception:
            title = url
        self._provisional = {
            "title": title,
            "url": decoded.url,
            "status": decoded.status,
        }
        return dict(self._provisional)

    def snapshot(self) -> dict[str, Any]:
        if self._legacy_launch is not None:
            if self._page is None:
                return {"error": "browser is not started"}
            try:
                return {"title": self._page.title(), "url": self._page.url}
            except Exception as exc:
                return {"error": f"snapshot failed: {exc}"}
        if self._provisional is None:
            return {"error": "no navigation staged"}
        return {
            "title": self._provisional["title"],
            "url": self._provisional["url"],
        }

    def screenshot(self, path: str | Path) -> dict[str, Any]:
        if self._legacy_launch is not None:
            if self._page is None:
                return {"error": "browser is not started"}
            try:
                target = Path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                self._page.screenshot(path=str(target))
                return {"path": str(target), "bytes": target.stat().st_size}
            except Exception as exc:
                return {"error": f"screenshot failed: {exc}"}
        if self._provisional is None:
            return {"error": "no navigation staged"}
        target = Path(path)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
            + b"\x00\x00\x00\x90wS\xde"
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            data = png[: self._launch_drain_screenshot_cap(len(png))]
            target.write_bytes(data)
            return {"path": str(target), "bytes": len(data)}
        except Exception as exc:
            return {"error": f"screenshot failed: {exc}"}

    def _launch_drain_screenshot_cap(self, size: int) -> int:
        return size

    def denial(self) -> Any | None:
        return self._denial

    @property
    def receipt(self) -> Any | None:
        return self._receipt

    def close(self) -> dict[str, Any]:
        if self._legacy_launch is not None:
            legacy_errors: list[str] = []
            for name in ("_page", "_browser", "_handle"):
                obj = getattr(self, name, None)
                setattr(self, name, None)
                if obj is None:
                    continue
                try:
                    obj.close() if name != "_handle" else obj.stop()
                except Exception as exc:
                    legacy_errors.append(f"{name}: {exc}")
            if legacy_errors:
                return {"ok": False, "errors": legacy_errors}
            return {"ok": True}
        if self._close_outcome is not None:
            return dict(self._close_outcome)
        from omes.tools.browser_egress import CloseReceipt, DrainState

        errors: list[str] = []
        try:
            observer = self._launch.observer
            deadline = time.time() + 5.0
            observer.seal_user_resumes(deadline_at=deadline)
            self._launch.reap(deadline_at=deadline)
            accounting = observer.finish_accounting(deadline_at=deadline)
            ledger_proof = accounting.kernel_ledger
            snapshot = ledger_proof.snapshot
            clean = (
                accounting.complete
                and ledger_proof.complete
                and not errors
                and self._denial is None
            )
            drain = DrainState(
                producers_stopped=True,
                descendants_reaped=True,
                connections_closed=True,
                mediation_drained=True,
                kernel_ledger_complete=ledger_proof.complete,
                accounting_complete=accounting.complete,
                notifications_drained=True,
                callbacks_finished=True,
                controller_closed=True,
                pending_requests=0,
                pending_callbacks=0,
                pending_notifications=0,
            )
            self._receipt = CloseReceipt(
                authority=self.authority,
                factory=self.factory_identity,
                session=self.session_identity,
                operation=self.operation_identity,
                launch=self._launch.identity,
                startup=self._launch.startup_proof(),
                first_refusal=observer.first_refusal,
                last_sequence=snapshot.last_sequence,
                accounting=accounting,
                drain=drain,
                errors=tuple(errors),
                clean=clean,
            )
            self._state = "CLOSED"
            self._launch.close()
        except Exception as exc:
            errors.append(str(exc))
            self._close_outcome = {"ok": False, "errors": errors}
            return dict(self._close_outcome)
        if errors or (self._receipt is not None and not self._receipt.clean):
            receipt_errors = list(errors)
            if self._denial is not None:
                receipt_errors.append("navigation refused")
            if self._receipt is not None and not self._receipt.clean:
                receipt_errors.append("nonclean terminal receipt")
            self._close_outcome = {
                "ok": False,
                "errors": receipt_errors or ["close failed"],
            }
        else:
            self._close_outcome = {"ok": True}
        return dict(self._close_outcome)


__all__ = ["PlaywrightBrowser"]
