"""Real browser transport on Playwright (sync API, headless Chromium).

Speaks the `BrowserSession` shape (`navigate`/`snapshot`) plus `screenshot`.
The `launch()` seam builds the Playwright browser; tests inject a stub so
no browser binary is needed. Real use needs `playwright install chromium`
once on the operator machine.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def _default_launch() -> Any:
    from playwright.sync_api import sync_playwright

    handle = sync_playwright().start()
    browser = handle.chromium.launch(headless=True)
    return handle, browser


class PlaywrightBrowser:
    """Headless Chromium behind navigate/snapshot/screenshot."""

    def __init__(self, launch: Callable[[], Any] | None = None) -> None:
        self._launch = launch or _default_launch
        self._handle: Any = None
        self._browser: Any = None
        self._page: Any = None

    def start(self) -> dict[str, Any]:
        """Launch the browser and open one page."""
        if self._page is not None:
            return {"ok": True, "open": True}
        launched = self._launch()
        if isinstance(launched, tuple):
            self._handle, self._browser = launched
        else:
            self._browser = launched
        self._page = self._browser.new_page()
        return {"ok": True, "open": True}

    def navigate(self, url: str) -> dict[str, Any]:
        """Go to `url`. Return title, final URL, and status."""
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

    def snapshot(self) -> dict[str, Any]:
        """Return the current page's title and URL."""
        if self._page is None:
            return {"error": "browser is not started"}
        try:
            return {"title": self._page.title(), "url": self._page.url}
        except Exception as exc:
            return {"error": f"snapshot failed: {exc}"}

    def screenshot(self, path: str | Path) -> dict[str, Any]:
        """Capture the viewport PNG to `path`. Return path + byte count."""
        if self._page is None:
            return {"error": "browser is not started"}
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(target))
            return {"path": str(target), "bytes": target.stat().st_size}
        except Exception as exc:
            return {"error": f"screenshot failed: {exc}"}

    def close(self) -> dict[str, Any]:
        """Close page, browser, and the Playwright handle."""
        errors: list[str] = []
        for name in ("_page", "_browser", "_handle"):
            obj = getattr(self, name)
            setattr(self, name, None)
            if obj is None:
                continue
            try:
                obj.close() if name != "_handle" else obj.stop()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        if errors:
            return {"ok": False, "errors": errors}
        return {"ok": True}


__all__ = ["PlaywrightBrowser"]
