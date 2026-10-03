"""Interactive device backends: adb, simctl, and Appium.

Each backend lists devices and captures screenshots behind an injectable
runner; only `AppiumDevice` also acts (tap/type/back). Runners default to
real subprocess/HTTP calls; tests inject stubs. No live devices in tests.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Callable


class DeviceError(RuntimeError):
    """A device failure naming the backend and the operation."""


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, timeout=timeout)


class AdbDevice:
    """Android devices via the adb CLI (list + screenshot, no actions)."""

    name = "adb"
    platform = "android"

    def __init__(self, run: Callable[..., Any] | None = None) -> None:
        self._run = run or _run

    def list_devices(self) -> list[dict[str, str]]:
        """Parse `adb devices -l` into id/model/state rows."""
        try:
            run = self._run(["adb", "devices", "-l"], timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeviceError(f"adb list_devices: {exc}") from exc
        if run.returncode != 0:
            raise DeviceError(f"adb list_devices: exit {run.returncode}")
        devices = []
        for line in run.stdout.decode("utf-8", "replace").splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2 or parts[1] == "offline":
                continue
            model = ""
            for part in parts[2:]:
                if part.startswith("model:"):
                    model = part.split(":", 1)[1]
            devices.append({"id": parts[0], "platform": "android",
                            "name": model or parts[0], "state": parts[1]})
        return devices

    def screenshot(self, device_id: str, path: str | Path) -> dict[str, Any]:
        """Capture `exec-out screencap -p` to `path`."""
        target = Path(path)
        try:
            run = self._run(["adb", "-s", device_id, "exec-out", "screencap", "-p"],
                            timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeviceError(f"adb screenshot: {exc}") from exc
        if run.returncode != 0 or not run.stdout.startswith(b"\x89PNG"):
            raise DeviceError("adb screenshot: no PNG returned")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(run.stdout)
        return {"path": str(target), "bytes": len(run.stdout)}


class SimctlDevice:
    """iOS simulators via xcrun simctl (list + screenshot, no actions)."""

    name = "simctl"
    platform = "ios"

    def __init__(self, run: Callable[..., Any] | None = None) -> None:
        self._run = run or _run

    def list_devices(self) -> list[dict[str, str]]:
        """Parse `simctl list devices available` into rows."""
        try:
            run = self._run(["xcrun", "simctl", "list", "devices", "available"], timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeviceError(f"simctl list_devices: {exc}") from exc
        if run.returncode != 0:
            raise DeviceError(f"simctl list_devices: exit {run.returncode}")
        devices = []
        for line in run.stdout.decode("utf-8", "replace").splitlines():
            match = re.match(r"\s+(.+?) \(([0-9A-F-]{36})\) \((Booted|Shutdown)\)", line)
            if match:
                devices.append({"id": match.group(2), "platform": "ios",
                                "name": match.group(1), "state": match.group(3).lower()})
        return devices

    def screenshot(self, device_id: str, path: str | Path) -> dict[str, Any]:
        """Capture `io <device> screenshot` to `path`."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            run = self._run(["xcrun", "simctl", "io", device_id, "screenshot", str(target)],
                            timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeviceError(f"simctl screenshot: {exc}") from exc
        if run.returncode != 0 or not target.is_file():
            raise DeviceError("simctl screenshot: no file produced")
        return {"path": str(target), "bytes": target.stat().st_size}


class AppiumDevice:
    """Appium server devices: screenshot plus tap/type/back actions."""

    name = "appium"
    platform = "any"

    def __init__(self, server: str = "http://127.0.0.1:4723",
                 connect: Callable[..., Any] | None = None) -> None:
        self.server = server
        self._connect = connect or self._default_connect

    def _default_connect(self, capabilities: dict) -> Any:
        from appium import webdriver
        from appium.options.android import UiAutomator2Options
        from appium.options.ios import XCUITestOptions

        platform = str(capabilities.get("platformName", "")).lower()
        options = XCUITestOptions() if platform == "ios" else UiAutomator2Options()
        options.load_capabilities(capabilities)
        return webdriver.Remote(self.server, options=options)

    def list_devices(self) -> list[dict[str, str]]:
        """Appium has no device enumeration; report the server endpoint."""
        return [{"id": self.server, "platform": "any",
                 "name": f"appium@{self.server}", "state": "unknown"}]

    def screenshot(self, device_id: str, path: str | Path,
                   capabilities: dict | None = None) -> dict[str, Any]:
        """Open a session, save the screenshot, quit the session."""
        del device_id
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            driver = self._connect(dict(capabilities or {}))
            try:
                ok = driver.save_screenshot(str(target))
            finally:
                driver.quit()
        except Exception as exc:
            raise DeviceError(f"appium screenshot: {exc}") from exc
        if not ok or not target.is_file():
            raise DeviceError("appium screenshot: no file produced")
        return {"path": str(target), "bytes": target.stat().st_size}

    def act(self, device_id: str, action: dict, capabilities: dict | None = None) -> dict[str, Any]:
        """One tap/type/back on a fresh session. `action` names `kind` + args."""
        del device_id
        kind = action.get("kind")
        if kind not in ("tap", "type", "back"):
            raise DeviceError(f"appium act: unknown kind {kind!r}")
        try:
            driver = self._connect(dict(capabilities or {}))
            try:
                if kind == "tap":
                    driver.tap([(int(action["x"]), int(action["y"]))])
                elif kind == "type":
                    from selenium.webdriver.common.action_chains import ActionChains

                    ActionChains(driver).send_keys(str(action["text"])).perform()
                else:
                    driver.back()
            finally:
                driver.quit()
        except DeviceError:
            raise
        except Exception as exc:
            raise DeviceError(f"appium act({kind}): {exc}") from exc
        return {"ok": True, "kind": kind}


__all__ = ["AdbDevice", "AppiumDevice", "DeviceError", "SimctlDevice"]
