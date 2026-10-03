"""Web pack: desk web tools + rendered review as an Omes registry family.

Ports `services/desk-gateway/src/desk_gateway/tools/web.py` (Vercel
lifecycle, preview checks, bundle secret scans) and adds `web_review_page`:
connectivity + rendered screenshot + vision analysis in one report. The
Vercel client, HTTP fetcher, browser factory, and vision transport are
injected seams; tests use fakes only.
"""

from __future__ import annotations

import hashlib
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

from omes.credentials.redact import redact_text
from omes.tools.playwright_browser import PlaywrightBrowser
from omes.tools.registry import ToolRegistry
from omes.tools.vision import vision_analyze

WEB_TOOL_NAMES = (
    "web_vercel_deployments",
    "web_vercel_promote",
    "web_vercel_rollback",
    "web_preview_check",
    "web_bundle_secret_scan",
    "web_review_page",
)

FETCH_TIMEOUT = 15.0


def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}


def _default_fetch(url: str, timeout: float = FETCH_TIMEOUT) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "omes-bot/preview-check"},
                                     method="GET")
    opener = urllib.request.build_opener(NoRedirects)
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(2_000_000)
            return {"status": response.status, "headers": dict(response.headers),
                    "body": body, "ms": round((time.monotonic() - started) * 1000, 1)}
    except Exception as exc:
        return {"error": f"upstream_error: fetch failed: {type(exc).__name__}"}


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so the report shows the original response."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class WebContext:
    """Everything the web tools need. Clients default to unconfigured."""

    root: str | Path = "."
    vercel: Any = None
    fetch: Any = None
    browser_factory: Any = None
    vision: Any = None
    artifacts_dir: str | Path = "artifacts/reviews"


class WebClient:
    """Desk web tools + rendered review bound to one context."""

    def __init__(self, ctx: WebContext) -> None:
        self.ctx = ctx

    def vercel_deployments(self, project: str, deployment_id: str | None = None,
                           limit: int = 10) -> dict[str, Any]:
        """List deployments, or fetch one. Project allowlist gated."""
        blocked = self._project_allowed(project)
        if blocked:
            return {"deployments": [], **blocked}
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if deployment_id:
            result = self.ctx.vercel.deployment(deployment_id)
            if not isinstance(result, dict) or result.get("error"):
                return result if isinstance(result, dict) else {"error": "upstream_error: no object"}
            return {"deployment": result.get("body")}
        result = self.ctx.vercel.deployments(project, int(limit))
        if not isinstance(result, dict) or result.get("error"):
            return {"deployments": [], **(result if isinstance(result, dict) else {"error": "upstream_error"})}
        body = result.get("body") or {}
        items = [{k: d.get(k) for k in ("uid", "state", "target", "url", "created", "meta")}
                 for d in body.get("deployments") or []]
        return {"deployments": items}

    def vercel_promote(self, project: str, deployment_id: str) -> dict[str, Any]:
        """Promote one deployment to production. Approval-gated at registration."""
        blocked = self._project_allowed(project)
        if blocked:
            return blocked
        if not isinstance(deployment_id, str) or deployment_id == "":
            raise ValueError("deployment_id must be a non-empty string")
        result = self.ctx.vercel.promote(project, deployment_id)
        if not isinstance(result, dict) or result.get("error"):
            reason = result.get("reason", "promote failed") if isinstance(result, dict) else "promote failed"
            code = result.get("error", "upstream_error") if isinstance(result, dict) else "upstream_error"
            return _error(str(code), str(reason))
        return {"ok": True, "result": result.get("body")}

    def vercel_rollback(self, project: str, deployment_id: str) -> dict[str, Any]:
        """Roll production back to one deployment. Approval-gated at registration."""
        blocked = self._project_allowed(project)
        if blocked:
            return blocked
        if not isinstance(deployment_id, str) or deployment_id == "":
            raise ValueError("deployment_id must be a non-empty string")
        result = self.ctx.vercel.rollback(project, deployment_id)
        if not isinstance(result, dict) or result.get("error"):
            reason = result.get("reason", "rollback failed") if isinstance(result, dict) else "rollback failed"
            code = result.get("error", "upstream_error") if isinstance(result, dict) else "upstream_error"
            return _error(str(code), str(reason))
        return {"ok": True, "result": result.get("body")}

    def preview_check(self, url: str, expect_status: int = 200) -> dict[str, Any]:
        """Fetch one URL: status, latency, content hash, redirect. No redirects followed."""
        if not isinstance(url, str) or url.strip() == "":
            raise ValueError("url must be a non-empty string")
        if isinstance(expect_status, bool) or not isinstance(expect_status, int):
            raise ValueError("expect_status must be an integer")
        host = urlparse(url).hostname or ""
        fetch = self.ctx.fetch or _default_fetch
        result = fetch(url, FETCH_TIMEOUT)
        if not isinstance(result, dict) or result.get("error"):
            return result if isinstance(result, dict) else {"error": "upstream_error: no object"}
        body = result.get("body", b"")
        if isinstance(body, str):
            body = body.encode("utf-8")
        return {
            "url": url, "host": host, "status": result.get("status"), "expected": expect_status,
            "matches": result.get("status") == expect_status, "ms": result.get("ms"),
            "content_type": (result.get("headers") or {}).get("content-type"),
            "body_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
            "redirect": (result.get("headers") or {}).get("location"),
        }

    def bundle_secret_scan(self, paths: list[str]) -> dict[str, Any]:
        """Scan repo-relative bundle files for credential shapes."""
        if not isinstance(paths, list) or not paths or any(not _repo_relative(p) for p in paths):
            return _error("invalid_args", "paths must be a non-empty list of repo-relative paths")
        root = Path(self.ctx.root)
        missing = [p for p in paths if not (root / p).is_file()]
        if missing:
            return _error("not_found", f"not under this root: {missing[:5]}")
        findings: list[dict[str, Any]] = []
        for rel in paths:
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return _error("upstream_error", f"cannot read {rel}: {exc}")
            for number, line in enumerate(text.splitlines(), start=1):
                if redact_text(line) != line:
                    findings.append({"path": rel, "line": number})
                    if len(findings) >= 50:
                        break
            if len(findings) >= 50:
                break
        return {"ok": not findings, "gate": "G-3", "findings": findings}

    def review_page(self, url: str, question: str, expect_status: int = 200,
                    name: str | None = None) -> dict[str, Any]:
        """Connectivity + rendered screenshot + vision analysis in one report."""
        if not isinstance(question, str) or question == "":
            raise ValueError("question must be a non-empty string")
        connectivity = self.preview_check(url, expect_status=expect_status)
        if connectivity.get("error"):
            return {"url": url, "connectivity": connectivity, "error": "connectivity failed"}
        factory = self.ctx.browser_factory or PlaywrightBrowser
        browser = factory()
        try:
            started = browser.start()
            if started.get("error"):
                return {"url": url, "connectivity": connectivity, "error": started["error"]}
            navigated = browser.navigate(url)
            if navigated.get("error"):
                return {"url": url, "connectivity": connectivity, "error": navigated["error"]}
            shot_name = (name or f"review-{abs(hash(url)) % 10**8}") + ".png"
            shot = browser.screenshot(str(Path(self.ctx.artifacts_dir) / shot_name))
            if shot.get("error"):
                return {"url": url, "connectivity": connectivity, "page": navigated,
                        "error": shot["error"]}
        finally:
            try:
                browser.close()
            except Exception:
                pass
        vision = vision_analyze(self.ctx.vision, shot["path"], question)
        return {"url": url, "connectivity": connectivity, "page": navigated,
                "screenshot": shot, "vision": vision}

    def _project_allowed(self, project: Any) -> dict[str, Any] | None:
        if not isinstance(project, str) or project == "":
            raise ValueError("project must be a non-empty string")
        if self.ctx.vercel is None:
            return _error("not_configured", "Vercel is not configured")
        if not self.ctx.vercel.allowed(project):
            return _error("forbidden", f"{project} is not in the Vercel project allowlist")
        return None


def _repo_relative(path: Any) -> bool:
    if not isinstance(path, str) or path == "":
        return False
    candidate = PurePosixPath(path)
    return not candidate.is_absolute() and ".." not in candidate.parts


def register_web_tools(registry: ToolRegistry, client: WebClient) -> list[str]:
    """Register the 6 web tools. Promote/rollback need approval."""

    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    handlers = {
        "web_vercel_deployments": lambda project, deployment_id=None, limit=10: _wrap(
            client.vercel_deployments, project, deployment_id=deployment_id, limit=limit),
        "web_vercel_promote": lambda project, deployment_id: _wrap(client.vercel_promote, project, deployment_id),
        "web_vercel_rollback": lambda project, deployment_id: _wrap(client.vercel_rollback, project, deployment_id),
        "web_preview_check": lambda url, expect_status=200: _wrap(client.preview_check, url, expect_status=expect_status),
        "web_bundle_secret_scan": lambda paths: _wrap(client.bundle_secret_scan, paths),
        "web_review_page": lambda url, question, expect_status=200, name=None: _wrap(
            client.review_page, url, question, expect_status=expect_status, name=name),
    }
    if set(handlers) != set(WEB_TOOL_NAMES):
        raise RuntimeError("Web tool handlers drifted from WEB_TOOL_NAMES")
    for name in WEB_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name],
                          requires_approval=name in ("web_vercel_promote", "web_vercel_rollback"))
    return list(WEB_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "web_vercel_deployments": ("List Vercel deployments, or fetch one. Read-only.",
                               _object({"project": _string("Project slug."), "deployment_id": _string("One deployment."),
                                        "limit": {"type": "integer"}}, ["project"])),
    "web_vercel_promote": ("Promote one deployment to production. Requires approval.",
                           _object({"project": _string("Project slug."), "deployment_id": _string("Deployment id.")},
                                   ["project", "deployment_id"])),
    "web_vercel_rollback": ("Roll production back to one deployment. Requires approval.",
                            _object({"project": _string("Project slug."), "deployment_id": _string("Deployment id.")},
                                    ["project", "deployment_id"])),
    "web_preview_check": ("Fetch one URL: status, latency, hash. Read-only.",
                          _object({"url": _string("URL to fetch."), "expect_status": {"type": "integer"}}, ["url"])),
    "web_bundle_secret_scan": ("Scan bundle files for credential shapes. Read-only.",
                               _object({"paths": {"type": "array", "items": {"type": "string"}}}, ["paths"])),
    "web_review_page": ("Connectivity + screenshot + vision analysis in one report. Read-only.",
                        _object({"url": _string("Page URL."), "question": _string("Vision question."),
                                 "expect_status": {"type": "integer"}, "name": _string("Screenshot stem.")}, ["url", "question"])),
}


__all__ = ["WEB_TOOL_NAMES", "WebClient", "WebContext", "register_web_tools"]
