# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Prometheus registry, HTTP/tool metrics, and the /metrics endpoint."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from omega_prime.grokbot.interceptors import (
    ToolCall,
    ToolDenial,
    ToolOutcome,
    run_tool_call,
)
from omega_prime.grokbot.metrics import (
    CONTENT_TYPE,
    MetricsInterceptor,
    MetricsMiddleware,
    MetricsRegistry,
    metrics_endpoint,
    record_auth_failure,
    register_build_info,
)
from omega_prime.grokbot.security import Principal


def _lines(registry: MetricsRegistry) -> list[str]:
    return registry.render().splitlines()


# ------------------------------------------------------------------------- registry


def test_empty_registry_renders_nothing() -> None:
    assert MetricsRegistry().render() == ""


def test_golden_exposition_text() -> None:
    reg = MetricsRegistry()
    counter = reg.counter("req_total", "Requests.\nSecond line \\ here", ("path",))
    counter.labels(path='a"b\\c\nd').inc()
    counter.labels(path='a"b\\c\nd').inc(2)
    gauge = reg.gauge("temp", "Temperature.")
    gauge.set(2.5)
    histogram = reg.histogram("lat_seconds", "Latency.", ("op",), buckets=(0.5, 1))
    child = histogram.labels(op="x")
    for value in (0.25, 0.75, 4):
        child.observe(value)

    assert reg.render() == (
        "# HELP req_total Requests.\\nSecond line \\\\ here\n"
        "# TYPE req_total counter\n"
        'req_total{path="a\\"b\\\\c\\nd"} 3\n'
        "# HELP temp Temperature.\n"
        "# TYPE temp gauge\n"
        "temp 2.5\n"
        "# HELP lat_seconds Latency.\n"
        "# TYPE lat_seconds histogram\n"
        'lat_seconds_bucket{op="x",le="0.5"} 1\n'
        'lat_seconds_bucket{op="x",le="1"} 2\n'
        'lat_seconds_bucket{op="x",le="+Inf"} 3\n'
        'lat_seconds_sum{op="x"} 5\n'
        'lat_seconds_count{op="x"} 3\n'
    )


def test_histogram_buckets_are_cumulative_and_inclusive() -> None:
    reg = MetricsRegistry()
    hist = reg.histogram("h", "h", buckets=(1, 2, 3))
    for value in (1, 1, 2, 3, 100):
        hist.observe(value)
    lines = _lines(reg)
    assert 'h_bucket{le="1"} 2' in lines
    assert 'h_bucket{le="2"} 3' in lines
    assert 'h_bucket{le="3"} 4' in lines
    assert 'h_bucket{le="+Inf"} 5' in lines
    assert "h_count 5" in lines
    assert "h_sum 107" in lines


def test_default_buckets_and_trailing_inf_are_normalised() -> None:
    reg = MetricsRegistry()
    reg.histogram("a", "a").observe(0.03)
    reg.histogram("b", "b", buckets=(1.0, float("inf"))).observe(0.5)
    text = reg.render()
    assert 'a_bucket{le="0.005"} 0' in text
    assert 'a_bucket{le="0.05"} 1' in text
    assert 'a_bucket{le="10"} 1' in text
    assert text.count('b_bucket{le="+Inf"}') == 1


def test_control_characters_in_label_values_cannot_break_lines() -> None:
    reg = MetricsRegistry()
    reg.counter("c", "c", ("v",)).labels(v="a\rb\x00c\u0085d\u00e9").inc()
    text = reg.render()
    assert 'c{v="a\\\\u000db\\\\u0000c\\\\u0085d\u00e9"} 1' in text
    assert len(text.splitlines()) == 3


def test_unlabeled_metrics_render_zero_before_use() -> None:
    reg = MetricsRegistry()
    reg.counter("c", "c")
    reg.gauge("g", "g")
    assert "c 0" in _lines(reg)
    assert "g 0" in _lines(reg)


def test_gauge_inc_dec_set() -> None:
    reg = MetricsRegistry()
    gauge = reg.gauge("g", "g", ("k",))
    child = gauge.labels(k="v")
    child.set(10)
    child.inc(5)
    child.dec(3)
    assert 'g{k="v"} 12' in _lines(reg)


def test_label_validation() -> None:
    reg = MetricsRegistry()
    counter = reg.counter("c", "c", ("a", "b"))
    with pytest.raises(ValueError):
        counter.labels(a="1")
    with pytest.raises(ValueError):
        counter.labels(a="1", b="2", c="3")
    with pytest.raises(ValueError):
        counter.labels(a="1", c="3")
    with pytest.raises(ValueError):
        counter.labels(a="1", b=2)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        counter.inc()  # labeled metric needs .labels()
    with pytest.raises(ValueError):
        reg.counter("bad name", "x")
    with pytest.raises(ValueError):
        reg.counter("ok", "x", ("1bad",))
    with pytest.raises(ValueError):
        reg.counter("ok2", "x", ("__reserved",))
    with pytest.raises(ValueError):
        reg.counter("ok3", "x", ("a", "a"))
    with pytest.raises(ValueError):
        reg.histogram("ok4", "x", ("le",))


def test_value_validation() -> None:
    reg = MetricsRegistry()
    with pytest.raises(ValueError):
        reg.counter("c", "c").inc(-1)
    with pytest.raises(ValueError):
        reg.histogram("h", "h").observe(float("nan"))
    with pytest.raises(ValueError):
        reg.histogram("bad", "x", buckets=(2, 1))
    with pytest.raises(ValueError):
        reg.histogram("bad2", "x", buckets=(float("nan"),))


def test_same_name_same_type_returns_existing_and_conflicts_raise() -> None:
    reg = MetricsRegistry()
    first = reg.counter("m", "help", ("a",))
    assert reg.counter("m", "other help", ("a",)) is first
    with pytest.raises(ValueError, match="already registered"):
        reg.gauge("m", "help", ("a",))
    with pytest.raises(ValueError, match="labels"):
        reg.counter("m", "help", ("b",))
    hist = reg.histogram("h", "h", buckets=(1, 2))
    assert reg.histogram("h", "h", buckets=(1, 2)) is hist
    with pytest.raises(ValueError, match="buckets"):
        reg.histogram("h", "h", buckets=(1, 3))


def test_child_cap_folds_extra_label_sets_into_overflow() -> None:
    reg = MetricsRegistry(max_children=2)
    counter = reg.counter("c", "c", ("k", "j"))
    for value in ("a", "b", "c", "d", "e"):
        counter.labels(k=value, j="x").inc()
    counter.labels(k="a", j="x").inc()  # existing child still addressable
    lines = [line for line in _lines(reg) if line.startswith("c{")]
    assert lines == [
        'c{k="a",j="x"} 2',
        'c{k="b",j="x"} 1',
        'c{k="overflow",j="overflow"} 3',
    ]


def test_updates_are_thread_safe() -> None:
    reg = MetricsRegistry()
    counter = reg.counter("c", "c", ("k",))
    hist = reg.histogram("h", "h")

    def work() -> None:
        for _ in range(500):
            counter.labels(k="v").inc()
            hist.observe(0.001)
            reg.render()

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    lines = _lines(reg)
    assert 'c{k="v"} 4000' in lines
    assert "h_count 4000" in lines


# ------------------------------------------------------------------- HTTP middleware


async def _ok(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def _accepted(request: Request) -> PlainTextResponse:
    return PlainTextResponse("accepted", status_code=202)


async def _redirect(request: Request) -> PlainTextResponse:
    return PlainTextResponse("", status_code=302, headers={"location": "/x"})


async def _teapot(request: Request) -> PlainTextResponse:
    return PlainTextResponse("no", status_code=418)


def _starlette() -> Starlette:
    return Starlette(
        routes=[
            Route("/healthz", _ok),
            Route("/messages/{sid}", _accepted, methods=["POST"]),
            Route("/admin/approvals/{tool}", _ok),
            Route("/moved", _redirect),
            Route("/teapot", _teapot),
            Route("/other/{n}", _ok),
        ]
    )


def test_middleware_groups_paths_and_status_classes() -> None:
    reg = MetricsRegistry()
    client = TestClient(MetricsMiddleware(_starlette(), reg))
    assert client.get("/healthz?token=supersecretvalue").status_code == 200
    assert client.post("/messages/abc123").status_code == 202
    assert client.get("/admin/approvals/deploy").status_code == 200
    assert client.get("/moved", follow_redirects=False).status_code == 302
    assert client.get("/teapot").status_code == 418
    assert client.get("/other/12345").status_code == 200
    assert client.get("/missing/xyz").status_code == 404
    assert client.get("/mcpx").status_code == 404  # not on a segment boundary

    text = reg.render()
    for expected in (
        'omega_http_requests_total{method="GET",path="/healthz",status="2xx"} 1',
        'omega_http_requests_total{method="POST",path="/messages",status="2xx"} 1',
        'omega_http_requests_total{method="GET",path="/admin",status="2xx"} 1',
        'omega_http_requests_total{method="GET",path="other",status="2xx"} 1',
        'omega_http_requests_total{method="GET",path="other",status="3xx"} 1',
        'omega_http_requests_total{method="GET",path="other",status="4xx"} 3',
        "omega_http_in_flight 0",
        'omega_http_request_duration_seconds_count{method="GET",path="/healthz"} 1',
    ):
        assert expected in text
    for leaked in ("supersecretvalue", "abc123", "12345", "xyz", "deploy"):
        assert leaked not in text


def test_middleware_custom_path_groups_and_passthrough() -> None:
    reg = MetricsRegistry()
    middleware = MetricsMiddleware(_starlette(), reg, path_groups=("/healthz",))
    assert middleware.group_path("/healthz") == "/healthz"
    assert middleware.group_path("/healthz/x") == "/healthz"
    assert middleware.group_path("/sse") == "other"


async def _drive(app: ASGIApp, *, method: str = "GET", path: str = "/sse") -> None:
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    await app(scope, receive, send)


def test_streaming_response_is_observed_at_response_start() -> None:
    reg = MetricsRegistry()
    observed: dict[str, Any] = {}

    async def run() -> None:
        gate = asyncio.Event()

        async def stream_app(scope: Scope, receive: Receive, send: Send) -> None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")],
                }
            )
            await send({"type": "http.response.body", "body": b"a", "more_body": True})
            await gate.wait()  # an SSE stream that has not ended yet
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        middleware = MetricsMiddleware(stream_app, reg)
        task = asyncio.create_task(_drive(middleware))
        for _ in range(200):
            await asyncio.sleep(0.005)
            if 'path="/sse",status="2xx"} 1' in reg.render():
                break
        observed["text"] = reg.render()
        gate.set()
        await asyncio.wait_for(task, timeout=2)
        observed["after"] = reg.render()

    asyncio.run(run())
    assert (
        'omega_http_requests_total{method="GET",path="/sse",status="2xx"} 1'
        in (observed["text"])
    )
    assert "omega_http_in_flight 1" in observed["text"]
    assert (
        'omega_http_request_duration_seconds_count{method="GET",path="/sse"} 1'
        in (observed["text"])
    )
    assert "omega_http_in_flight 0" in observed["after"]
    assert 'status="2xx"} 1' in observed["after"]  # not double counted


def test_exception_before_response_counts_5xx_and_restores_in_flight() -> None:
    reg = MetricsRegistry()

    async def boom(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(_drive(MetricsMiddleware(boom, reg), path="/mcp"))
    text = reg.render()
    assert 'omega_http_requests_total{method="GET",path="/mcp",status="5xx"} 1' in text
    assert "omega_http_in_flight 0" in text


def test_non_http_scopes_are_passed_through_untouched() -> None:
    reg = MetricsRegistry()
    seen: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    async def run() -> None:
        async def receive() -> Message:
            return {"type": "lifespan.startup"}

        async def send(message: Message) -> None:
            return None

        await MetricsMiddleware(app, reg)({"type": "lifespan"}, receive, send)

    asyncio.run(run())
    assert seen == ["lifespan"]
    assert "omega_http_requests_total{" not in reg.render()


# --------------------------------------------------------------------- interceptor


def _call(name: str = "echo") -> ToolCall:
    return ToolCall(name=name, arguments={}, principal=None)


class _Deny:
    def before(self, call: ToolCall) -> ToolDenial | None:
        del call
        return ToolDenial("rate_limited", "slow down", 1.0)

    def after(self, call: ToolCall, outcome: ToolOutcome) -> None:
        del call, outcome


def test_interceptor_records_ok_error_and_denied_calls() -> None:
    reg = MetricsRegistry()
    metrics = MetricsInterceptor(reg, tool_names=lambda: {"echo", "boom"})

    run_tool_call([metrics], _call(), lambda: json.dumps({"ok": True}))
    run_tool_call([metrics], _call(), lambda: json.dumps({"error": "bad"}))
    run_tool_call([metrics, _Deny()], _call("boom"), lambda: "{}")

    text = reg.render()
    assert 'omega_tool_calls_total{tool="boom",status="denied"} 1' in text
    assert 'omega_tool_calls_total{tool="echo",status="error"} 1' in text
    assert 'omega_tool_calls_total{tool="echo",status="ok"} 1' in text
    assert 'omega_tool_denials_total{code="rate_limited"} 1' in text
    assert 'omega_tool_call_duration_seconds_count{tool="echo"} 2' in text
    assert "omega_tool_calls_in_flight 0" in text


def test_interceptor_counts_dispatch_exceptions_and_balances_in_flight() -> None:
    reg = MetricsRegistry()
    metrics = MetricsInterceptor(reg, tool_names=lambda: ["echo"])

    def explode() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_tool_call([metrics], _call(), explode)
    text = reg.render()
    assert 'omega_tool_calls_total{tool="echo",status="error"} 1' in text
    assert "omega_tool_calls_in_flight 0" in text


def test_interceptor_in_flight_is_visible_during_dispatch() -> None:
    reg = MetricsRegistry()
    metrics = MetricsInterceptor(reg, tool_names=lambda: ["echo"])
    during: list[str] = []

    def dispatch() -> str:
        during.append(reg.render())
        return "{}"

    run_tool_call([metrics], _call(), dispatch)
    assert "omega_tool_calls_in_flight 1" in during[0]


def test_unknown_tool_names_cannot_create_labels() -> None:
    reg = MetricsRegistry()
    metrics = MetricsInterceptor(reg, tool_names=lambda: {"echo"})
    run_tool_call([metrics], _call("attacker-chosen-name-1"), lambda: "{}")
    run_tool_call([metrics], _call("attacker-chosen-name-2"), lambda: "{}")
    text = reg.render()
    assert 'omega_tool_calls_total{tool="unknown",status="ok"} 2' in text
    assert "attacker" not in text


def test_failing_tool_names_callback_degrades_to_unknown() -> None:
    reg = MetricsRegistry()

    def broken() -> set[str]:
        raise RuntimeError("no list")

    metrics = MetricsInterceptor(reg, tool_names=broken)
    run_tool_call([metrics], _call(), lambda: "{}")
    assert 'omega_tool_calls_total{tool="unknown",status="ok"} 1' in reg.render()


# --------------------------------------------------------------------- helpers


def test_record_auth_failure_bounds_the_reason() -> None:
    reg = MetricsRegistry()
    on_failure = record_auth_failure(reg)
    for reason in ("missing", "missing", "malformed", "invalid", "weird", None):
        on_failure({"reason": reason, "path": "/x", "client": "1.2.3.4"})
    on_failure({"reason": "<script>"})
    on_failure({})
    lines = _lines(reg)
    assert 'omega_auth_failures_total{reason="missing"} 2' in lines
    assert 'omega_auth_failures_total{reason="malformed"} 1' in lines
    assert 'omega_auth_failures_total{reason="invalid"} 1' in lines
    assert 'omega_auth_failures_total{reason="other"} 4' in lines
    assert "weird" not in reg.render()


def test_register_build_info() -> None:
    reg = MetricsRegistry()
    register_build_info(reg, version="1", package_version="2.0.0")
    register_build_info(reg, version="1", package_version="2.0.0")
    assert 'omega_build_info{version="1",package_version="2.0.0"} 1' in _lines(reg)


# --------------------------------------------------------------------- endpoint


class _InjectPrincipal:
    def __init__(self, app: ASGIApp, principal: Principal | None) -> None:
        self.app = app
        self.principal = principal

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.principal is not None:
            scope.setdefault("state", {})["principal"] = self.principal
        await self.app(scope, receive, send)


def _endpoint_client(
    reg: MetricsRegistry, principal: Principal | None, **kwargs: Any
) -> TestClient:
    app = Starlette(routes=[Route("/metrics", metrics_endpoint(reg, **kwargs))])
    return TestClient(_InjectPrincipal(app, principal))


def test_metrics_endpoint_requires_a_principal_with_the_scope() -> None:
    reg = MetricsRegistry()
    register_build_info(reg, version="1", package_version="9")

    missing = _endpoint_client(reg, None).get("/metrics")
    assert missing.status_code == 401
    assert "omega_build_info" not in missing.text

    no_scope = _endpoint_client(reg, Principal("p", frozenset())).get("/metrics")
    assert no_scope.status_code == 403
    assert "omega_build_info" not in no_scope.text

    reader = Principal("reader", frozenset({"read"}))
    ok = _endpoint_client(reg, reader).get("/metrics")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == CONTENT_TYPE
    assert ok.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert ok.headers["cache-control"] == "no-store"
    assert ok.text == reg.render()

    admin_only = _endpoint_client(reg, reader, required_scope="admin")
    assert admin_only.get("/metrics").status_code == 403
    admin = Principal("root", frozenset({"admin"}))
    assert (
        _endpoint_client(reg, admin, required_scope="admin").get("/metrics").status_code
        == 200
    )
