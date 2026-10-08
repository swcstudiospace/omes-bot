"""App packs: desk packs tools as an Omega Prime registry family.

Ports `services/desk-gateway/src/desk_gateway/tools/packs.py`: pack
load/unload with the live-tools ceiling, plus the shared pack backends
(API smoke, Supabase read-only query, push test, feature flags, crash
reports, scoreboard, store listing, render-job status). Pack tools talk
to the application's own API base; without one they report
not_configured. The pack table, API bases, and HTTP client are
injected; tests use fakes only.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from omega_prime.credentials.redact import redact_text
from omega_prime.tools.registry import ToolRegistry

PACKS_TOOL_NAMES = (
    "app_tools_load",
    "app_api_smoke",
    "app_supabase_query",
    "app_push_test",
    "app_feature_flags",
    "app_crash_reports",
    "app_scoreboard_get",
    "app_store_listing_get",
    "app_render_job_status",
)

MAX_LIVE_TOOLS = 20

READ_ONLY_SQL = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum|call|do|merge|set\s+role)\b",
    re.IGNORECASE,
)


def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}


def read_only_sql(sql: str) -> str | None:
    """Desk guard verbatim: SELECT/WITH only, no write keywords, one statement."""
    if not READ_ONLY_SQL.match(sql):
        return "only SELECT or WITH statements are accepted"
    if FORBIDDEN_SQL.search(sql):
        return "statement contains a write keyword"
    if ";" in sql.rstrip(";"):
        return "one statement per call"
    return None


def _default_http(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """urllib-backed request returning the desk HttpUpstream result shape."""
    if params:
        query = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        )
        url = f"{url}?{query}" if query else url
    data = None
    merged = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        merged.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=merged, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_000)
            status = response.status
    except Exception as exc:
        return {
            "error": "upstream_error",
            "reason": redact_text(f"{type(exc).__name__}: {exc}")[:300],
        }
    try:
        body = json.loads(raw.decode("utf-8"))
    except ValueError:
        body = {"text": redact_text(raw[:2000].decode("utf-8", "replace"))}
    if status >= 400:
        return {
            "error": "upstream_error",
            "reason": f"app api returned HTTP {status}",
            "status": status,
            "body": body,
        }
    return {"ok": True, "status": status, "body": body}


@dataclass
class PacksContext:
    """Everything the pack tools need. No app is configured by default."""

    packs: dict[str, dict[str, Any]] = field(default_factory=dict)
    api_bases: dict[str, str] = field(default_factory=dict)
    http: Any = None
    absorbed: tuple[str, ...] = ("web", "android", "ios")
    timeout: float = 10.0


class PacksClient:
    """Desk packs tools bound to one context. Loaded packs live in memory."""

    def __init__(self, ctx: PacksContext) -> None:
        self.ctx = ctx
        self.loaded: dict[str, list[dict[str, Any]]] = {}

    def _http(self) -> Any:
        return self.ctx.http if self.ctx.http is not None else _default_http

    def _live_tools(self) -> int:
        return sum(
            len((self.ctx.packs.get(app) or {}).get("tools") or [])
            for app in self.loaded
        )

    def tools_load(
        self, app: str, task_id: str, unload: bool = False
    ) -> dict[str, Any]:
        """Load or unload an application tool pack for one ticket."""
        pack = self.ctx.packs.get(app)
        if pack is None:
            return _error(
                "not_found", f"no pack named {app}", available=sorted(self.ctx.packs)
            )
        seats = pack.get("seats") or []
        if not [seat for seat in seats if seat in self.ctx.absorbed]:
            return _error(
                "forbidden", f"pack {app} is not declared for an absorbed seat"
            )
        if unload:
            records = self.loaded.pop(app, [])
            return {"ok": True, "loaded": records, "live_tools": self._live_tools()}
        current = [name for name in self.loaded if name != app]
        projected = sum(
            len((self.ctx.packs.get(name) or {}).get("tools") or []) for name in current
        ) + len(pack.get("tools") or [])
        if projected > MAX_LIVE_TOOLS:
            return _error(
                "ceiling",
                f"loading {app} would put {projected} tools live; "
                f"the ceiling is {MAX_LIVE_TOOLS}. Unload a pack first",
            )
        record = {"app": app, "task_id": task_id}
        self.loaded.setdefault(app, []).append(record)
        records = [rec for name in sorted(self.loaded) for rec in self.loaded[name]]
        return {
            "ok": True,
            "loaded": records,
            "tools": sorted(pack.get("tools") or []),
            "live_tools": self._live_tools(),
            "note": "loaded set recorded; call the pack through the app_* backends",
        }

    def _base(self, app: str) -> str:
        return (self.ctx.api_bases.get(app) or "").rstrip("/")

    def _api(self, app: str, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        base = self._base(app)
        if not base:
            return {
                "error": "not_configured",
                "reason": f"{app} API base is not configured",
            }
        return self._http()(method, f"{base}{path}", timeout=self.ctx.timeout, **kwargs)

    def api_smoke(self, app: str, environment: str = "staging") -> dict[str, Any]:
        """GET the app's /health endpoint and report status + latency."""
        if not self._base(app):
            return _error("not_configured", f"{app} API base is not configured")
        started = time.monotonic()
        result = self._api(
            app, "GET", "/health", headers={"X-Desk-Environment": environment}
        )
        ms = round((time.monotonic() - started) * 1000, 1)
        if result.get("error"):
            return {**result, "ms": ms, "environment": environment}
        return {
            "ok": True,
            "environment": environment,
            "status": result.get("status"),
            "ms": ms,
            "body": result.get("body"),
        }

    def supabase_query(self, app: str, sql: str, limit: int = 50) -> dict[str, Any]:
        """Run a read-only SQL statement through the app's /desk/query endpoint."""
        problem = read_only_sql(sql)
        if problem:
            return _error("invalid_sql", problem)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not self._base(app):
            return {
                "rows": [],
                **_error("not_configured", f"{app} API base is not configured"),
            }
        return self._api(
            app, "POST", "/desk/query", json_body={"sql": sql, "limit": limit}
        )

    def push_test(
        self,
        app: str,
        platform: str,
        device_label: str,
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Send a test push to a registered test device. Approval-gated."""
        if not self._base(app):
            return _error("not_configured", f"{app} API base is not configured")
        payload = {
            "platform": platform,
            "device_label": device_label,
            "title": title,
            "body": body,
            "test_only": True,
        }
        result = self._api(app, "POST", "/desk/push-test", json_body=payload)
        if result.get("error"):
            return _error(result["error"], result.get("reason", "push test failed"))
        return {"ok": True, "result": result.get("body")}

    def feature_flags(self, app: str, environment: str = "staging") -> dict[str, Any]:
        """Current feature flags for one environment."""
        if not self._base(app):
            return {
                "flags": {},
                **_error("not_configured", f"{app} API base is not configured"),
            }
        result = self._api(
            app, "GET", "/desk/flags", params={"environment": environment}
        )
        return result if result.get("error") else {"flags": result.get("body")}

    def crash_reports(
        self,
        app: str,
        platform: str | None = None,
        since_hours: int = 24,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Recent crash groups for one app."""
        if not self._base(app):
            return {
                "groups": [],
                **_error("not_configured", f"{app} API base is not configured"),
            }
        params = {
            k: v
            for k, v in {
                "platform": platform,
                "since_hours": since_hours,
                "limit": limit,
            }.items()
            if v is not None
        }
        result = self._api(app, "GET", "/desk/crashes", params=params)
        return result if result.get("error") else {"groups": result.get("body")}

    def scoreboard_get(self, app: str, limit: int = 20) -> dict[str, Any]:
        """Current lane standings from the app's scoreboard endpoint."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not self._base(app):
            return {
                "lanes": [],
                **_error("not_configured", f"{app} API base is not configured"),
            }
        result = self._api(app, "GET", "/api/scoreboard", params={"limit": limit})
        return result if result.get("error") else {"lanes": result.get("body")}

    def store_listing_get(
        self, app: str, store: str, locale: str = "en-AU"
    ) -> dict[str, Any]:
        """Current store listing text and assets manifest for one store."""
        if not self._base(app):
            return _error("not_configured", f"{app} API base is not configured")
        result = self._api(
            app, "GET", "/desk/store-listing", params={"store": store, "locale": locale}
        )
        return result if result.get("error") else {"listing": result.get("body")}

    def render_job_status(
        self, app: str, job_id: str, environment: str = "staging"
    ) -> dict[str, Any]:
        """Status of one render job."""
        if not self._base(app):
            return _error("not_configured", f"{app} API base is not configured")
        try:
            result = self._api(
                app,
                "GET",
                f"/api/render-jobs/{job_id}",
                headers={"X-Desk-Environment": environment},
            )
        except Exception as exc:
            return _error("upstream_error", type(exc).__name__)
        return result if result.get("error") else {"job": result.get("body")}


APPROVAL_TOOLS = frozenset({"app_tools_load", "app_push_test"})


def register_packs_tools(registry: ToolRegistry, client: PacksClient) -> list[str]:
    """Register the 9 app pack tools. Load and push test need approval."""

    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    handlers: dict[str, Callable[..., Any]] = {
        "app_tools_load": lambda app, task_id, unload=False: _wrap(
            client.tools_load, app, task_id, unload=unload
        ),
        "app_api_smoke": lambda app, environment="staging": _wrap(
            client.api_smoke, app, environment
        ),
        "app_supabase_query": lambda app, sql, limit=50: _wrap(
            client.supabase_query, app, sql, limit
        ),
        "app_push_test": lambda app, platform, device_label, title=None, body=None: (
            _wrap(client.push_test, app, platform, device_label, title, body)
        ),
        "app_feature_flags": lambda app, environment="staging": _wrap(
            client.feature_flags, app, environment
        ),
        "app_crash_reports": lambda app, platform=None, since_hours=24, limit=10: _wrap(
            client.crash_reports, app, platform, since_hours, limit
        ),
        "app_scoreboard_get": lambda app, limit=20: _wrap(
            client.scoreboard_get, app, limit
        ),
        "app_store_listing_get": lambda app, store, locale="en-AU": _wrap(
            client.store_listing_get, app, store, locale
        ),
        "app_render_job_status": lambda app, job_id, environment="staging": _wrap(
            client.render_job_status, app, job_id, environment
        ),
    }
    if set(handlers) != set(PACKS_TOOL_NAMES):
        raise RuntimeError("App pack tool handlers drifted from PACKS_TOOL_NAMES")
    for name in PACKS_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=(name in APPROVAL_TOOLS),
        )
    return list(PACKS_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "app_tools_load": (
        "Load or unload an application tool pack. Requires approval.",
        _object(
            {
                "app": _string("Pack name."),
                "task_id": _string("Ticket id."),
                "unload": {"type": "boolean"},
            },
            ["app", "task_id"],
        ),
    ),
    "app_api_smoke": (
        "Hit the app API health endpoint. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "environment": _string("staging or production."),
            },
            ["app"],
        ),
    ),
    "app_supabase_query": (
        "Read-only SQL through the app API. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "sql": _string("SELECT/WITH only."),
                "limit": {"type": "integer"},
            },
            ["app", "sql"],
        ),
    ),
    "app_push_test": (
        "Send a test push to a test device. Requires approval.",
        _object(
            {
                "app": _string("Pack name."),
                "platform": _string("android or ios."),
                "device_label": _string("Registered test device."),
                "title": _string("Push title."),
                "body": _string("Push body."),
            },
            ["app", "platform", "device_label"],
        ),
    ),
    "app_feature_flags": (
        "Feature flags for one environment. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "environment": _string("staging or production."),
            },
            ["app"],
        ),
    ),
    "app_crash_reports": (
        "Recent crash groups. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "platform": _string("android or ios."),
                "since_hours": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            ["app"],
        ),
    ),
    "app_scoreboard_get": (
        "Lane standings from the scoreboard endpoint. Read-only.",
        _object({"app": _string("Pack name."), "limit": {"type": "integer"}}, ["app"]),
    ),
    "app_store_listing_get": (
        "Store listing text and assets manifest. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "store": _string("Store id."),
                "locale": _string("Locale."),
            },
            ["app", "store"],
        ),
    ),
    "app_render_job_status": (
        "Status of one render job. Read-only.",
        _object(
            {
                "app": _string("Pack name."),
                "job_id": _string("Job id."),
                "environment": _string("staging or production."),
            },
            ["app", "job_id"],
        ),
    ),
}


__all__ = [
    "MAX_LIVE_TOOLS",
    "PACKS_TOOL_NAMES",
    "PacksClient",
    "PacksContext",
    "read_only_sql",
    "register_packs_tools",
]
