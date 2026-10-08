"""Web pack: desk web tools + rendered review as an Omega Prime registry family.

Ports `services/desk-gateway/src/desk_gateway/tools/web.py` (Vercel
lifecycle, preview checks, bundle secret scans) and adds `web_review_page`:
connectivity + rendered screenshot + vision analysis in one report. The
Vercel client, HTTP fetcher, browser factory, and vision transport are
injected seams; tests use fakes only.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from omega_prime.credentials.redact import redact_text
from omega_prime.providers.destination import (
    DestinationDenied,
    DestinationTransport,
    SafeFetch,
)
from omega_prime.tools.registry import ToolRegistry
from omega_prime.tools.vision import vision_analyze

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


def _safe_shot_name(name: str) -> str | None:
    """`<stem>.png` confined to the artifacts dir, else None."""
    stem = name[:-4] if name.endswith(".png") else name
    if not stem or stem in (".", "..") or "/" in stem or "\\" in stem:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.~-]*", stem):
        return None
    return stem + ".png"


@dataclass
class WebContext:
    """Everything the web tools need. Clients default to unconfigured."""

    root: str | Path = "."
    vercel: Any = None
    fetch: SafeFetch | None = None
    transport: DestinationTransport | None = None
    policy: Any = None
    browser_factory: Any = None
    vision: Any = None
    artifacts_dir: str | Path = "artifacts/reviews"
    allowed_hosts: tuple[str, ...] | None = None


class WebClient:
    """Desk web tools + rendered review bound to one context."""

    def __init__(self, ctx: WebContext) -> None:
        self.ctx = ctx

    def vercel_deployments(
        self, project: str, deployment_id: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """List deployments, or fetch one. Project allowlist gated."""
        blocked = self._project_allowed(project)
        if blocked:
            return {"deployments": [], **blocked}
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if deployment_id:
            result = self.ctx.vercel.deployment(deployment_id)
            if not isinstance(result, dict) or result.get("error"):
                return (
                    result
                    if isinstance(result, dict)
                    else {"error": "upstream_error: no object"}
                )
            return {"deployment": result.get("body")}
        result = self.ctx.vercel.deployments(project, int(limit))
        if not isinstance(result, dict) or result.get("error"):
            return {
                "deployments": [],
                **(result if isinstance(result, dict) else {"error": "upstream_error"}),
            }
        body = result.get("body") or {}
        items = [
            {k: d.get(k) for k in ("uid", "state", "target", "url", "created", "meta")}
            for d in body.get("deployments") or []
        ]
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
            reason = (
                result.get("reason", "promote failed")
                if isinstance(result, dict)
                else "promote failed"
            )
            code = (
                result.get("error", "upstream_error")
                if isinstance(result, dict)
                else "upstream_error"
            )
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
            reason = (
                result.get("reason", "rollback failed")
                if isinstance(result, dict)
                else "rollback failed"
            )
            code = (
                result.get("error", "upstream_error")
                if isinstance(result, dict)
                else "upstream_error"
            )
            return _error(str(code), str(reason))
        return {"ok": True, "result": result.get("body")}

    def preview_check(
        self, url: str, expect_status: int = 200, *, operation: Any = None
    ) -> dict[str, Any]:
        """Fetch one URL: status, latency, content hash, redirect. No redirects followed."""
        if not isinstance(url, str) or url.strip() == "":
            raise ValueError("url must be a non-empty string")
        if isinstance(expect_status, bool) or not isinstance(expect_status, int):
            raise ValueError("expect_status must be an integer")
        fetch = self.ctx.fetch
        transport = self.ctx.transport
        if fetch is None or transport is None:
            return {
                "url": url,
                "error": "not_configured: preview transport is not configured",
            }
        if not isinstance(fetch, SafeFetch):
            return {
                "url": url,
                "error": "not_configured: preview transport is not configured",
            }
        if fetch.transport is not transport:
            return {"url": url, "error": "not_configured: preview authority mismatch"}
        root = operation
        if root is None:
            root = transport.current_operation()
        owned = False
        if root is None:
            root = transport.begin_operation(
                deadline_at=transport._clock.monotonic() + 15.0
            )
            owned = True
        else:
            bound = transport.current_operation()
            if bound is not None and bound is not root:
                return {
                    "url": url,
                    "error": "not_configured: conflicting bound operation",
                }
        if owned:
            try:
                binding = transport.bind_operation(root)
                with binding:
                    result = fetch(url, FETCH_TIMEOUT, operation=root)
            except DestinationDenied as exc:
                result = {"error": f"{exc.refusal.public_code}: {exc.refusal.message}"}
            finally:
                with contextlib.suppress(Exception):
                    transport.finish_operation(
                        root, deadline_at=transport._clock.monotonic() + 5.0
                    )
        else:
            try:
                result = fetch(url, FETCH_TIMEOUT, operation=root)
            except DestinationDenied as exc:
                result = {"error": f"{exc.refusal.public_code}: {exc.refusal.message}"}
        if not isinstance(result, dict) or result.get("error"):
            if isinstance(result, dict) and result.get("error"):
                return {"url": url, "error": result["error"]}
            return {"url": url, "error": "upstream_error: no object"}
        body = result.get("body", b"")
        if isinstance(body, str):
            body = body.encode("utf-8")
        if not isinstance(body, (bytes, bytearray)):
            return {"url": url, "error": "upstream_error: bad body"}
        body = bytes(body)
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            host = ""
        headers_dict = result.get("headers")
        headers = headers_dict if isinstance(headers_dict, dict) else {}
        return {
            "url": url,
            "host": host,
            "status": result.get("status"),
            "expected": expect_status,
            "matches": result.get("status") == expect_status,
            "ms": result.get("ms"),
            "content_type": headers.get("content-type"),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "redirect": headers.get("location"),
        }

    def bundle_secret_scan(self, paths: list[str]) -> dict[str, Any]:
        """Scan repo-relative bundle files for credential shapes."""
        if (
            not isinstance(paths, list)
            or not paths
            or any(not _repo_relative(p) for p in paths)
        ):
            return _error(
                "invalid_args", "paths must be a non-empty list of repo-relative paths"
            )
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

    def review_page(
        self,
        url: str,
        question: str,
        expect_status: int = 200,
        name: str | None = None,
        *,
        operation: Any = None,
    ) -> dict[str, Any]:
        """Connectivity + rendered screenshot + vision analysis in one report."""
        if not isinstance(question, str) or question == "":
            raise ValueError("question must be a non-empty string")

        transport = self.ctx.transport
        if (
            transport is not None
            and getattr(self.ctx, "fetch", None) is not None
            and getattr(self.ctx.fetch, "transport", None) is not transport
        ):
            return {"url": url, "error": "not_configured: preview authority mismatch"}
        root = operation
        if root is None and transport is not None:
            root = transport.current_operation()
        owned = False
        if root is None and transport is not None:
            root = transport.begin_operation(
                deadline_at=transport._clock.monotonic() + 30.0
            )
            owned = True
        elif transport is not None and root is not None:
            bound = transport.current_operation()
            if bound is not None and bound is not root:
                return {
                    "url": url,
                    "error": "not_configured: conflicting bound operation",
                }

        def _execute_review() -> dict[str, Any]:
            connectivity = self.preview_check(
                url, expect_status=expect_status, operation=root
            )
            if connectivity.get("error"):
                return {
                    "url": url,
                    "connectivity": connectivity,
                    "error": "connectivity failed",
                }
            factory = self.ctx.browser_factory
            if factory is None:
                return {
                    "url": url,
                    "connectivity": connectivity,
                    "error": "not_configured: browser_factory is required",
                }
            create_session = getattr(factory, "create_session", None)
            if callable(create_session) and root is not None:
                browser = create_session(operation=root)
            elif callable(factory):
                try:
                    browser = factory()
                except TypeError as exc:
                    return {
                        "url": url,
                        "connectivity": connectivity,
                        "error": f"invalid browser factory: {exc}",
                    }
            else:
                return {"url": url, "error": "invalid browser factory"}

            receipt = None
            close_outcome = None
            browser_any: Any = browser
            try:
                started = browser_any.start()
                if started.get("error"):
                    return {
                        "url": url,
                        "connectivity": connectivity,
                        "error": started["error"],
                    }
                navigated = browser_any.navigate(url)
                if navigated.get("error"):
                    return {
                        "url": url,
                        "connectivity": connectivity,
                        "error": navigated["error"],
                    }
                shot_name = _safe_shot_name(name or f"review-{abs(hash(url)) % 10**8}")
                if shot_name is None:
                    return {
                        "url": url,
                        "connectivity": connectivity,
                        "page": navigated,
                        "error": "invalid_name: screenshot name stays inside the artifacts dir",
                    }
                shot = browser_any.screenshot(
                    str(Path(self.ctx.artifacts_dir) / shot_name)
                )
                if shot.get("error"):
                    return {
                        "url": url,
                        "connectivity": connectivity,
                        "page": navigated,
                        "error": shot["error"],
                    }
            finally:
                with contextlib.suppress(Exception):
                    close_outcome = browser_any.close()
                receipt_getter = getattr(browser_any, "receipt", None)
                if callable(receipt_getter):
                    receipt = receipt_getter()
                elif receipt_getter is not None:
                    receipt = receipt_getter

            if close_outcome is not None and not close_outcome.get("ok", True):
                return {
                    "url": url,
                    "connectivity": connectivity,
                    "page": navigated,
                    "error": "browser close failed",
                    "close": close_outcome,
                }
            owns_fn = getattr(factory, "owns", None)
            if (
                callable(owns_fn)
                and receipt is not None
                and not owns_fn(browser, receipt)
            ):
                return {
                    "url": url,
                    "connectivity": connectivity,
                    "page": navigated,
                    "error": "foreign browser receipt",
                }
            if receipt is not None and not getattr(receipt, "clean", True):
                return {
                    "url": url,
                    "connectivity": connectivity,
                    "page": navigated,
                    "error": "browser session was not clean",
                }

            vision = vision_analyze(self.ctx.vision, shot["path"], question)
            return {
                "url": url,
                "connectivity": connectivity,
                "page": navigated,
                "screenshot": shot,
                "vision": vision,
            }

        if owned and transport is not None and root is not None:
            drain_error = None
            try:
                binding = transport.bind_operation(root)
                with binding:
                    outcome = _execute_review()
            finally:
                try:
                    drain = transport.finish_operation(
                        root, deadline_at=transport._clock.monotonic() + 5.0
                    )
                    if not getattr(drain, "complete", True) or bool(
                        getattr(drain, "pending_scopes", 0)
                    ):
                        drain_error = {
                            "url": url,
                            "error": "operation drain incomplete",
                        }
                except Exception as exc:
                    drain_error = {
                        "url": url,
                        "error": f"operation drain failed: {exc}",
                    }
            if drain_error is not None:
                return drain_error
            return outcome
        return _execute_review()

    def _project_allowed(self, project: Any) -> dict[str, Any] | None:
        if not isinstance(project, str) or project == "":
            raise ValueError("project must be a non-empty string")
        if self.ctx.vercel is None:
            return _error("not_configured", "Vercel is not configured")
        if not self.ctx.vercel.allowed(project):
            return _error(
                "forbidden", f"{project} is not in the Vercel project allowlist"
            )
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

    handlers: dict[str, Callable[..., Any]] = {
        "web_vercel_deployments": lambda project, deployment_id=None, limit=10: _wrap(
            client.vercel_deployments, project, deployment_id=deployment_id, limit=limit
        ),
        "web_vercel_promote": lambda project, deployment_id: _wrap(
            client.vercel_promote, project, deployment_id
        ),
        "web_vercel_rollback": lambda project, deployment_id: _wrap(
            client.vercel_rollback, project, deployment_id
        ),
        "web_preview_check": lambda url, expect_status=200: _wrap(
            client.preview_check, url, expect_status=expect_status
        ),
        "web_bundle_secret_scan": lambda paths: _wrap(client.bundle_secret_scan, paths),
        "web_review_page": lambda url, question, expect_status=200, name=None: _wrap(
            client.review_page, url, question, expect_status=expect_status, name=name
        ),
    }
    if set(handlers) != set(WEB_TOOL_NAMES):
        raise RuntimeError("Web tool handlers drifted from WEB_TOOL_NAMES")
    for name in WEB_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in ("web_vercel_promote", "web_vercel_rollback"),
        )
    return list(WEB_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "web_vercel_deployments": (
        "List Vercel deployments, or fetch one. Read-only.",
        _object(
            {
                "project": _string("Project slug."),
                "deployment_id": _string("One deployment."),
                "limit": {"type": "integer"},
            },
            ["project"],
        ),
    ),
    "web_vercel_promote": (
        "Promote one deployment to production. Requires approval.",
        _object(
            {
                "project": _string("Project slug."),
                "deployment_id": _string("Deployment id."),
            },
            ["project", "deployment_id"],
        ),
    ),
    "web_vercel_rollback": (
        "Roll production back to one deployment. Requires approval.",
        _object(
            {
                "project": _string("Project slug."),
                "deployment_id": _string("Deployment id."),
            },
            ["project", "deployment_id"],
        ),
    ),
    "web_preview_check": (
        "Fetch one URL: status, latency, hash. Read-only.",
        _object(
            {"url": _string("URL to fetch."), "expect_status": {"type": "integer"}},
            ["url"],
        ),
    ),
    "web_bundle_secret_scan": (
        "Scan bundle files for credential shapes. Read-only.",
        _object({"paths": {"type": "array", "items": {"type": "string"}}}, ["paths"]),
    ),
    "web_review_page": (
        "Connectivity + screenshot + vision analysis in one report. Read-only.",
        _object(
            {
                "url": _string("Page URL."),
                "question": _string("Vision question."),
                "expect_status": {"type": "integer"},
                "name": _string("Screenshot stem."),
            },
            ["url", "question"],
        ),
    ),
}


__all__ = ["WEB_TOOL_NAMES", "WebClient", "WebContext", "register_web_tools"]
