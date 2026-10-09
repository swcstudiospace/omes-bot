"""Tests for Remote SSE MCP Transport."""

from starlette.testclient import TestClient

from omega_prime.grokbot.manifest import find_repo_root
from omega_prime.grokbot.remote import create_mcp_sse_app


def test_mcp_sse_health_endpoints():
    root = find_repo_root()
    app = create_mcp_sse_app(root=root)
    client = TestClient(app)

    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "omega-prime-mcp-server"
    assert data["rostered_tools"] > 100

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True


def test_mcp_sse_auth_rejected():
    root = find_repo_root()
    app = create_mcp_sse_app(root=root, token="secure-key-12345")
    client = TestClient(app)

    # Health check works without auth
    res = client.get("/healthz")
    assert res.status_code == 200

    # SSE endpoint requires auth
    res_sse = client.get("/sse")
    assert res_sse.status_code == 401
    assert "Unauthorized" in res_sse.text

    # Invalid Bearer token
    res_bad = client.get("/sse", headers={"Authorization": "Bearer wrong-token"})
    assert res_bad.status_code == 401


def test_mcp_sse_auth_accepted():
    root = find_repo_root()
    app = create_mcp_sse_app(root=root, token="secure-key-12345")
    client = TestClient(app)

    # Messages endpoint with invalid token returns 401
    res_msg_bad = client.post(
        "/messages/?session_id=dummy", headers={"Authorization": "Bearer bad"}
    )
    assert res_msg_bad.status_code == 401

    # Messages endpoint with valid token bypasses auth check (returns 400/404 for unknown session, not 401)
    res_msg_ok = client.post(
        "/messages/?session_id=dummy",
        headers={"Authorization": "Bearer secure-key-12345"},
    )
    assert res_msg_ok.status_code != 401
