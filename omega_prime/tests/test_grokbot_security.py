# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Phase 62-01: bearer security core."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from omega_prime.grokbot.security import (
    MIN_TOKEN_LENGTH,
    SCOPE_ADMIN,
    SCOPE_CALL,
    SCOPE_READ,
    AuthMiddleware,
    Principal,
    SecurityConfigError,
    TokenStore,
    check_bind_safety,
    generate_token,
    hash_token,
    is_loopback_host,
    parse_bearer,
    principal_from_request,
    principal_from_scope,
)

TOKEN = "t" * 24 + "-valid-token"


def test_hash_token_is_sha256_hex():
    digest = hash_token("abc")
    assert digest == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_generate_token_prefix_and_uniqueness():
    first, second = generate_token(), generate_token("zz")
    assert first.startswith("omk_") and second.startswith("zz_")
    assert first != second
    assert len(first) > MIN_TOKEN_LENGTH


def test_token_store_hit_miss_empty_none():
    store = TokenStore.from_token(TOKEN, principal_id="alice", label="Alice")
    principal = store.verify(TOKEN)
    assert principal is not None and principal.id == "alice"
    assert principal.label == "Alice"
    assert store.verify(TOKEN + "x") is None
    assert store.verify("") is None
    assert store.verify(None) is None
    assert store.enabled
    assert not TokenStore().enabled
    assert TokenStore().verify(TOKEN) is None


def test_token_store_checks_every_entry(monkeypatch: pytest.MonkeyPatch):
    import omega_prime.grokbot.security as security

    reader = Principal("reader", frozenset({SCOPE_READ}))
    caller = Principal("caller", frozenset({SCOPE_CALL}))
    store = TokenStore(
        [(reader, hash_token("reader-token-0000")), (caller, hash_token(TOKEN))]
    )
    compared: list[bool] = []
    real = security.hmac.compare_digest

    def spy(left: Any, right: Any) -> bool:
        result = real(left, right)
        compared.append(result)
        return result

    monkeypatch.setattr(security.hmac, "compare_digest", spy)
    found = store.verify("reader-token-0000")
    assert found is not None and found.id == "reader"
    # the first entry matched, yet the second was still compared
    assert compared == [True, False]
    assert [p.id for p in store.principals()] == ["reader", "caller"]


def test_token_store_rejects_malformed_digest():
    with pytest.raises(SecurityConfigError):
        TokenStore([(Principal("x", frozenset()), "not-a-digest")])


def test_from_token_validates_length_and_scopes():
    with pytest.raises(SecurityConfigError):
        TokenStore.from_token("short")
    with pytest.raises(SecurityConfigError):
        TokenStore.from_token(TOKEN, scopes=["read", "root"])
    store = TokenStore.from_token(TOKEN)
    assert store.principals()[0].id == "env-token"
    assert store.principals()[0].scopes == frozenset({SCOPE_READ, SCOPE_CALL})
    assert TokenStore.from_token("x" * MIN_TOKEN_LENGTH).enabled


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc", "abc"),
        ("bearer abc", "abc"),
        ("BEARER abc", "abc"),
        ("Bearer  abc", None),
        ("Bearer a b", None),
        ("Bearer abc ", None),
        ("Bearer", None),
        ("Bearer ", None),
        ("Basic abc", None),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_bearer(header: str | None, expected: str | None):
    assert parse_bearer(header) == expected


def test_principal_scope_hierarchy():
    reader = Principal("r", frozenset({SCOPE_READ}))
    caller = Principal("c", frozenset({SCOPE_CALL}))
    admin = Principal("a", frozenset({SCOPE_ADMIN}))
    assert reader.allows(SCOPE_READ)
    assert not reader.allows(SCOPE_CALL) and not reader.allows(SCOPE_ADMIN)
    assert caller.allows(SCOPE_READ) and caller.allows(SCOPE_CALL)
    assert not caller.allows(SCOPE_ADMIN)
    assert all(admin.allows(s) for s in (SCOPE_READ, SCOPE_CALL, SCOPE_ADMIN))
    assert not admin.allows("root")
    assert not Principal("n", frozenset()).allows(SCOPE_READ)
    assert not Principal("u", frozenset({"bogus"})).allows(SCOPE_READ)


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("127.5.6.7", True),
        ("::1", True),
        ("[::1]", True),
        ("localhost", True),
        ("LOCALHOST", True),
        ("::ffff:127.0.0.1", True),
        ("0.0.0.0", False),
        ("::", False),
        ("", False),
        ("192.168.1.10", False),
        ("10.0.0.1", False),
        ("example.com", False),
        ("not a host", False),
    ],
)
def test_is_loopback_host(host: str, expected: bool):
    assert is_loopback_host(host) is expected


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
@pytest.mark.parametrize("auth", [True, False])
@pytest.mark.parametrize("insecure", [True, False])
def test_check_bind_safety_loopback_always_ok(host: str, auth: bool, insecure: bool):
    check_bind_safety(host, auth_enabled=auth, allow_insecure=insecure)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "", "10.1.2.3", "example.com"])
def test_check_bind_safety_non_loopback(host: str):
    check_bind_safety(host, auth_enabled=True, allow_insecure=False)
    check_bind_safety(host, auth_enabled=False, allow_insecure=True)
    with pytest.raises(SecurityConfigError, match="refusing to serve on"):
        check_bind_safety(host, auth_enabled=False, allow_insecure=False)


def _app(
    failures: list[dict[str, Any]] | None = None,
    *,
    raising: bool = False,
) -> Starlette:
    async def whoami(request: Request) -> JSONResponse:
        principal = request.state.principal
        scope_principal = principal_from_scope(request.scope)
        assert principal_from_request(request) is principal
        assert scope_principal is principal
        assert principal is not None
        return JSONResponse({"id": principal.id})

    async def health(request: Request) -> JSONResponse:
        return JSONResponse(
            {"ok": True, "principal": principal_from_request(request) is not None}
        )

    def on_failure(event: dict[str, Any]) -> None:
        if failures is not None:
            failures.append(event)
        if raising:
            raise RuntimeError("callback exploded")

    app = Starlette(
        routes=[
            Route("/whoami", whoami),
            Route("/healthz", health),
            Route("/readyz", health),
            Route("/healthz/extra", health),
        ]
    )
    app.add_middleware(
        AuthMiddleware,
        store=TokenStore.from_token(TOKEN, principal_id="alice"),
        on_failure=on_failure,
    )
    return app


def test_middleware_rejects_missing_header():
    failures: list[dict[str, Any]] = []
    response = TestClient(_app(failures)).get("/whoami")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Bearer realm="omega-prime"'
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"] == "unauthorized"
    assert failures[0]["reason"] == "missing"
    assert failures[0]["path"] == "/whoami"


def test_middleware_rejects_invalid_and_malformed():
    failures: list[dict[str, Any]] = []
    client = TestClient(_app(failures))
    invalid = client.get("/whoami", headers={"Authorization": "Bearer wrong-token"})
    malformed = client.get("/whoami", headers={"Authorization": "Basic abc"})
    spaced = client.get("/whoami", headers={"Authorization": "Bearer a b"})
    for response in (invalid, malformed, spaced):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == 'Bearer realm="omega-prime"'
    assert [f["reason"] for f in failures] == ["invalid", "malformed", "malformed"]
    assert all(set(f) == {"reason", "path", "client"} for f in failures)


def test_middleware_never_accepts_query_token():
    failures: list[dict[str, Any]] = []
    client = TestClient(_app(failures))
    for key in ("token", "access_token", "api_key"):
        response = client.get(f"/whoami?{key}={TOKEN}")
        assert response.status_code == 401
    assert [f["reason"] for f in failures] == ["missing"] * 3


def test_middleware_accepts_valid_header_and_sets_principal():
    client = TestClient(_app())
    response = client.get("/whoami", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"id": "alice"}
    lowercase = client.get("/whoami", headers={"Authorization": f"bearer {TOKEN}"})
    assert lowercase.status_code == 200


def test_middleware_public_paths_are_exact():
    client = TestClient(_app())
    for path in ("/healthz", "/readyz"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["principal"] is False
    assert client.get("/healthz/extra").status_code == 401


def test_failure_callback_never_receives_token_and_cannot_break_401():
    failures: list[dict[str, Any]] = []
    client = TestClient(_app(failures, raising=True))
    response = client.get(
        f"/whoami?token={TOKEN}",
        headers={"Authorization": "Bearer " + TOKEN + "-nope"},
    )
    assert response.status_code == 401
    assert TOKEN not in repr(failures)
    assert TOKEN not in response.text
    assert set(failures[0]) == {"reason", "path", "client"}


def test_principal_helpers_tolerate_missing_state():
    assert principal_from_request(None) is None
    assert principal_from_request(object()) is None
    assert principal_from_scope({}) is None
    assert principal_from_scope({"state": {}}) is None
    assert principal_from_scope({"state": {"principal": "not-a-principal"}}) is None
    principal = Principal("p", frozenset({SCOPE_READ}))
    assert principal_from_scope({"state": {"principal": principal}}) is principal
