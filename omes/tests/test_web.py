"""Phase 28: web tool family behind fakes; browser via stub launcher."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omes.tools.approvals import ApprovalLog
from omes.tools.playwright_browser import PlaywrightBrowser
from omes.tools.registry import ToolRegistry
from omes.tools.webpack import WebClient, WebContext, register_web_tools


class FakeVercel:
    def __init__(self, projects=("acme",)):
        self.projects = set(projects)
        self.calls: list[tuple] = []

    def allowed(self, project):
        return project in self.projects

    def deployments(self, project, limit):
        self.calls.append(("deployments", project, limit))
        return {
            "body": {
                "deployments": [
                    {
                        "uid": "d-1",
                        "state": "READY",
                        "target": "production",
                        "url": "acme.vercel.app",
                        "created": 1,
                        "meta": {},
                    }
                ]
            }
        }

    def deployment(self, deployment_id):
        self.calls.append(("deployment", deployment_id))
        return {"body": {"uid": deployment_id, "state": "READY"}}

    def promote(self, project, deployment_id):
        self.calls.append(("promote", project, deployment_id))
        return {"body": {"aliased": True}}

    def rollback(self, project, deployment_id):
        self.calls.append(("rollback", project, deployment_id))
        return {"body": {"aliased": True}}


def _fetch_ok(url, timeout):
    return {
        "status": 200,
        "headers": {"content-type": "text/html"},
        "body": b"<h1>hi</h1>",
        "ms": 12.5,
    }


class FakePage:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.url = "about:blank"
        self.closed = False

    def goto(self, url, wait_until=None):
        self.url = url
        return FakeResponse(200)

    def title(self):
        return "Acme"

    def screenshot(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG-fake")

    def close(self):
        self.closed = True


class FakeResponse:
    def __init__(self, status):
        self.status = status


class FakeBrowserPeer:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.page = FakePage(tmp_path)
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeVision:
    def analyze(self, image_url, question, region=None):
        return {"answer": f"saw {image_url}: {question}"}


def _ctx(tmp_path, **overrides):
    base = dict(
        root=tmp_path,
        vercel=FakeVercel(),
        fetch=_fetch_ok,
        browser_factory=lambda: PlaywrightBrowser(
            launch=lambda: FakeBrowserPeer(tmp_path)
        ),
        vision=FakeVision(),
        artifacts_dir=tmp_path / "shots",
    )
    base.update(overrides)
    return WebContext(**base)


def test_vercel_allowlist_and_shapes(tmp_path):
    client = WebClient(_ctx(tmp_path))
    listed = client.vercel_deployments("acme")
    assert listed["deployments"][0]["uid"] == "d-1"
    assert (
        client.vercel_deployments("acme", deployment_id="d-9")["deployment"]["uid"]
        == "d-9"
    )
    assert client.vercel_promote("acme", "d-1") == {
        "ok": True,
        "result": {"aliased": True},
    }
    assert client.vercel_rollback("acme", "d-1") == {
        "ok": True,
        "result": {"aliased": True},
    }
    assert "forbidden" in client.vercel_deployments("evil")["error"]
    assert "forbidden" in client.vercel_promote("evil", "d-1")["error"]
    bare = WebClient(WebContext(root=tmp_path))
    assert "not_configured" in bare.vercel_deployments("acme")["error"]


def test_preview_shape_mismatch_and_failure(tmp_path):
    client = WebClient(_ctx(tmp_path))
    ok = client.preview_check("https://acme.test/", expect_status=200)
    assert ok["matches"] is True and ok["status"] == 200 and ok["bytes"] == 11
    assert ok["host"] == "acme.test" and ok["redirect"] is None
    mismatch = client.preview_check("https://acme.test/", expect_status=201)
    assert mismatch["matches"] is False
    failing = WebClient(
        _ctx(
            tmp_path,
            fetch=lambda url, timeout: {"error": "upstream_error: fetch failed"},
        )
    )
    assert "fetch failed" in failing.preview_check("https://x/")["error"]
    with pytest.raises(ValueError, match="non-empty string"):
        client.preview_check("")
    assert "only http" in client.preview_check("file:///etc/passwd")["error"]
    assert "forbidden_host" in client.preview_check("http://localhost:9/")["error"]
    assert "forbidden_host" in client.preview_check("http://169.254.169.254/")["error"]
    assert "forbidden_host" in client.preview_check("http://10.0.0.9/")["error"]
    scoped = WebClient(_ctx(tmp_path, allowed_hosts=("acme.test",)))
    assert scoped.preview_check("https://acme.test/")["matches"] is True
    assert "allowlist" in scoped.preview_check("https://other.test/")["error"]


def test_bundle_scan_findings(tmp_path):
    (tmp_path / "app.js").write_text(
        "const key = 'sk-abcdefgh12345678';\n", encoding="utf-8"
    )
    (tmp_path / "clean.js").write_text("console.log(1);\n", encoding="utf-8")
    client = WebClient(_ctx(tmp_path))
    result = client.bundle_secret_scan(["app.js", "clean.js"])
    assert result["ok"] is False and result["gate"] == "G-3"
    assert result["findings"] == [{"path": "app.js", "line": 1}]
    assert client.bundle_secret_scan(["clean.js"])["ok"] is True
    assert "not under this root" in client.bundle_secret_scan(["missing.js"])["error"]
    assert "repo-relative" in client.bundle_secret_scan(["../x.js"])["error"]


def test_review_page_orchestrates_all_three(tmp_path):
    client = WebClient(_ctx(tmp_path))
    report = client.review_page(
        "https://acme.test/", "is the hero visible?", name="home"
    )
    assert report["connectivity"]["status"] == 200
    assert report["page"] == {
        "title": "Acme",
        "url": "https://acme.test/",
        "status": 200,
    }
    assert report["screenshot"]["path"].endswith("home.png")
    assert Path(report["screenshot"]["path"]).is_file()
    assert "hero visible" in report["vision"]["answer"]
    blind = WebClient(_ctx(tmp_path, vision=None))
    assert (
        "not configured"
        in blind.review_page("https://acme.test/", "q")["vision"]["error"]
    )
    failing = WebClient(
        _ctx(tmp_path, fetch=lambda url, timeout: {"error": "upstream_error: down"})
    )
    assert failing.review_page("https://x/", "q")["error"] == "connectivity failed"
    assert (
        "invalid_name"
        in client.review_page("https://acme.test/", "q", name="../../evil")["error"]
    )


def test_browser_lifecycle_and_errors(tmp_path):
    peer_holder: list = []

    def launch():
        peer = FakeBrowserPeer(tmp_path)
        peer_holder.append(peer)
        return peer

    browser = PlaywrightBrowser(launch=launch)
    assert browser.navigate("https://x/") == {"error": "browser is not started"}
    assert browser.start() == {"ok": True, "open": True}
    assert browser.snapshot() == {"title": "Acme", "url": "about:blank"}
    shot = browser.screenshot(tmp_path / "s.png")
    assert shot["bytes"] == 9 and Path(shot["path"]).is_file()
    assert browser.close() == {"ok": True}
    assert peer_holder[0].closed is True and peer_holder[0].page.closed is True
    assert browser.close() == {"ok": True}


def test_approvals_gate_promote_rollback_only(tmp_path):
    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log)
    register_web_tools(registry, WebClient(_ctx(tmp_path)))
    assert (
        json.loads(
            registry.dispatch("web_preview_check", {"url": "https://acme.test/"})
        )["status"]
        == 200
    )
    for tool in ("web_vercel_promote", "web_vercel_rollback"):
        assert json.loads(
            registry.dispatch(tool, {"project": "acme", "deployment_id": "d-1"})
        ) == {"error": "approval required", "tool": tool}
    assert log.approve("web_vercel_promote", "ada").get("approved") is True
    assert (
        json.loads(
            registry.dispatch(
                "web_vercel_promote", {"project": "acme", "deployment_id": "d-1"}
            )
        )["ok"]
        is True
    )
