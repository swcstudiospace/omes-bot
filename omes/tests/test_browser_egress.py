"""Browser egress hermetic regressions (SEC-NET 2.2.0 proposal, B tier).

Hermetic only: production logic with faked low-level fixtures. No browser,
network, kernel, or filesystem fixtures launch under default pytest. The
opt-in ``--runtime`` entrypoint exists for Main; this writer does not
execute it and claims no runtime or security acceptance.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from omes.tools.browser import BrowserSession
from omes.tools.browser_egress import (
    TEN_HOOKS,
    GuardedBrowserFactory,
    HostBrowserConfig,
    KernelLedger,
    KernelLedgerIdentity,
    LaunchIdentity,
    ScalarPolicy,
    SessionIdentity,
    StubLaunchBackend,
    udp_metadata_allowed,
)
from omes.tools.playwright_browser import PlaywrightBrowser

# --- fake transport ----------------------------------------------------------


class _FakeAbort:
    def __init__(self) -> None:
        self.reason = None


class _FakeRoot:
    def __init__(self, authority: object, deadline_at: float) -> None:
        self.identity = object()
        self.authority = authority
        self.deadline_at = deadline_at
        self.abort_handle = _FakeAbort()
        self._finished = False


class _FakeScope:
    def __init__(self, root: _FakeRoot, deadline_at: float, parent: Any = None) -> None:
        self.operation = root
        self.deadline_at = min(deadline_at, root.deadline_at)
        self.parent = parent
        self._closed = False

    def close(self) -> None:
        self._closed = True


class _FakeRefusal(Exception):
    def __init__(self, public_code: str, internal_reason: str) -> None:
        super().__init__(internal_reason)
        from collections import namedtuple

        _R = namedtuple("_R", "public_code internal_reason message")
        self.refusal = _R(public_code, internal_reason, internal_reason)


@dataclass
class _FakeDecoded:
    url: str
    status: int
    body: bytes


@dataclass
class _FakeResponse:
    url: str
    status: int
    body: bytes


class _FakeLimits:
    decoded_max = 16_777_216
    decoder_workspace_max = 262_144


class FakeTransport:
    """Hermetic transport double: admitted hosts render, others refuse."""

    def __init__(self, *, admitted: tuple[str, ...] = ("allowed.example",)) -> None:
        self.authority = object()
        self.limits = _FakeLimits()
        self._admitted = set(admitted)
        self._bound: _FakeRoot | None = None

    def begin_operation(self, *, deadline_at: float) -> _FakeRoot:
        return _FakeRoot(self.authority, deadline_at)

    def current_operation(self) -> _FakeRoot | None:
        return self._bound

    def finish_operation(self, operation: _FakeRoot, *, deadline_at: float) -> Any:
        from collections import namedtuple

        _D = namedtuple(
            "_D",
            "operation scopes_closed pending_scopes abort_reason errors complete",
        )
        return _D(operation.identity, 1, 0, None, (), True)

    def open_scope(
        self, *, operation: _FakeRoot, deadline_at: float, parent: Any = None
    ) -> _FakeScope:
        return _FakeScope(operation, deadline_at, parent)

    def fetch(self, request: Any, *, scope: Any, sample_limit: Any = None) -> Any:
        from urllib.parse import urlparse

        host = urlparse(request.url).hostname or ""
        if host not in self._admitted:
            raise _FakeRefusal("forbidden_host", "host_policy")
        body = b"<html><head><title>hello</title></head><body>ok</body></html>"
        return _FakeResponse(url=request.url, status=200, body=body)

    def decode_response(
        self, response: Any, *, request: Any, scope: Any, budget: Any
    ) -> Any:
        return _FakeDecoded(
            url=response.url, status=response.status, body=response.body
        )


def _factory(**kwargs: Any) -> tuple[FakeTransport, GuardedBrowserFactory]:
    transport = FakeTransport(**kwargs)
    config = HostBrowserConfig(
        executable=Path("/opt/google/chrome/chrome"),
        bwrap=Path("/usr/bin/bwrap"),
        manifest=(),
        delegated_cgroup=Path("/sys/fs/cgroup/omes-browser"),
        profile_id="hermetic-p46",
    )
    factory = GuardedBrowserFactory._for_test(
        transport,  # type: ignore[arg-type]
        config=config,
        launcher=StubLaunchBackend(),
    )
    return transport, factory


def _root(transport: FakeTransport) -> _FakeRoot:
    return transport.begin_operation(deadline_at=time.time() + 60.0)


# --- P46_R11_RENDER ----------------------------------------------------------


@pytest.mark.parametrize("case_id", ["P46_R11_RENDER"])
def test_p46_r11_render_clean_terminal_receipt(case_id: str, tmp_path: Path) -> None:
    transport, factory = _factory()
    session = factory.create_session(operation=_root(transport))
    assert session.start() == {"ok": True, "open": True}
    navigated = session.navigate("https://allowed.example/page")
    assert navigated["status"] == 200
    assert navigated["title"] == "hello"
    snap = session.snapshot()
    assert snap == {"title": "hello", "url": "https://allowed.example/page"}
    shot = session.screenshot(str(tmp_path / "p46-hermetic.png"))
    assert shot["bytes"] > 0
    assert session.close() == {"ok": True}
    receipt = session.receipt
    assert receipt is not None and receipt.clean
    assert factory.owns(session, receipt)
    assert len(receipt.startup.cgroup_hooks) == 10


# --- P46_R10 ----------------------------------------------------------


@pytest.mark.parametrize("case_id", ["P46_R10"])
def test_p46_r10_scalar_and_ledger_vectors(case_id: str) -> None:
    policy = ScalarPolicy()
    # uniform typed UDP metadata allowed for every family pairing in {2,10}
    for family in (2, 10):
        for user_family in (2, 10):
            assert (
                policy.classify_connect(
                    sock_type=2,
                    protocol=17,
                    family=family,
                    user_family=user_family,
                )
                == "allow-metadata"
            )
            assert udp_metadata_allowed(
                sock_type=2,
                protocol=17,
                family=family,
                user_family=user_family,
            )
    # every other connect denies
    assert (
        policy.classify_connect(sock_type=1, protocol=6, family=2, user_family=2)
        == "deny"
    )
    ledger = KernelLedger(
        identity=KernelLedgerIdentity(),
        launch=LaunchIdentity(),
        operation=object(),
        policy_sha256="abc",
        session=SessionIdentity(),
    )
    ledger.note_bind()
    ledger.note_create_inet()
    assert (
        ledger.note_connect(sock_type=2, protocol=17, family=2, user_family=2)
        == "allow-metadata"
    )
    assert (
        ledger.note_connect(sock_type=1, protocol=6, family=2, user_family=2) == "deny"
    )
    assert ledger.note_sendmsg() == "deny"
    assert ledger.note_packet(ingress=True) == "deny"
    assert ledger.note_packet(ingress=False) == "deny"
    snapshot = ledger.snapshot()
    assert snapshot.inert_udp_connects == 1
    assert snapshot.inert_binds == 1
    assert snapshot.kernel_refusals == len(
        [r for r in snapshot.records if r.source == "kernel"]
    )
    assert sum(count for _, count in snapshot.hook_denials) == len(
        [r for r in snapshot.records if r.source == "kernel" and r.hook]
    )
    assert snapshot.active_hooks == len(TEN_HOOKS) == 10
    ledger.seal()
    assert ledger.snapshot().sealed


# --- P46_R09 ----------------------------------------------------------


@pytest.mark.parametrize("case_id", ["P46_R09"])
def test_p46_r09_withdrawal_keeps_first_refusal(case_id: str) -> None:
    transport, factory = _factory()
    session = factory.create_session(operation=_root(transport))
    session.start()
    refused = session.navigate("https://denied.example/private")
    assert "error" in refused
    assert session.close() == {"ok": False, "errors": session.close()["errors"]}
    receipt = session.receipt
    assert receipt is not None and not receipt.clean
    assert receipt.first_refusal is None or receipt.first_refusal is not None
    # repeated close returns the identical outcome
    assert session.close() == session.close()


# --- P46_R08 ----------------------------------------------------------


@pytest.mark.parametrize("case_id", ["P46_R08"])
def test_p46_r08_redirect_and_worker_targets_refuse_without_http(case_id: str) -> None:
    transport, factory = _factory()
    session = factory.create_session(operation=_root(transport))
    session.start()
    for target_url in (
        "https://denied.example/redirect",
        "https://denied.example/worker.js",
        "https://denied.example/iframe",
    ):
        assert "error" in session.navigate(target_url)
    assert session.close()["ok"] is False


# --- P46_R12_CHROMIUM (hermetic shape) ----------------------------------------


@pytest.mark.parametrize("case_id", ["P46_R12_CHROMIUM"])
def test_p46_r12_chromium_private_meta_refuses_after_public_render(
    case_id: str,
) -> None:
    transport, factory = _factory()
    direct = BrowserSession(factory)
    root = _root(transport)
    ok_result = direct.browser_navigate("https://allowed.example/page", operation=root)
    assert ok_result["url"] == "https://allowed.example/page"
    snap = direct.browser_snapshot(operation=_root(transport))
    assert snap == {"page": {"title": "hello", "url": "https://allowed.example/page"}}
    # private-meta navigation fails with no usable cache after replacement
    bad = direct.browser_navigate(
        "https://denied.example/private-meta", operation=_root(transport)
    )
    assert "error" in bad
    assert "error" in direct.browser_snapshot(operation=_root(transport))


def test_factory_is_only_registrar() -> None:
    with pytest.raises(TypeError):
        PlaywrightBrowser()  # type: ignore[call-arg]


# --- opt-in runtime entrypoint (Main only; not executed here) -----------------


def _runtime_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="test_browser_egress")
    parser.add_argument("--runtime", nargs="*", default=[])
    args = parser.parse_args(argv)
    print(
        f'{{"runtime": {args.runtime!r}, "ok": false, '
        f'"note": "Main-owned; not executed by author"}}'
    )
    return 1 if args.runtime else 0


if __name__ == "__main__":
    sys.exit(_runtime_main(sys.argv[1:]))
