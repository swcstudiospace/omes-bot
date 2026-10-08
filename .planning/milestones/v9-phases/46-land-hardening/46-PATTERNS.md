# Phase 46: Land in-flight hardening - Pattern Map

**Mapped:** 2026-10-07
**Mode:** Native `plan:pre` / `gsd-pattern-mapper`, focused gap closure
**Files classified:** 14 proposed writer targets, plus 1 intentionally unchanged policy reference
**Target state:** 11 existing tracked targets; 3 proposed creations absent at the bounded path lookup
**Source-content files analyzed:** 5; no additional product/document bodies read
**Strong tracked source analogs:** 5
**Target assignments with source-style matches:** 10 / 14; 4 documentation targets have no inspected source-pattern analog
**Ownership:** Existing Linear SPE-7465 and SPE-7508; correlation `ut-muxyg46j-497dedf5`

## Scope and authority

This map supplies **existing-style evidence**, not a transport design, security acceptance or runtime receipt. The current gaps are T-46-08 (resolved destination/actual fetch peer) and T-46-12 (every browser request and mandatory egress enforcement). Both must be remediated; no waiver is authorized.

Mandatory inputs were read first: `46-CONTEXT.md`, `46-VERIFICATION.md`, `local://omega-security-before.md`, and `local://omega-p46-correction-route.json`. Additional scoped control inputs read were `local://omega-gsd-execution-contract.json`, `local://Tutmu-p46-contract.rework.assignment.md`, and `local://omega-swarm-brief.md`. The bounded phase-artifact lookup found no `*RESEARCH.md` and no prior `46-PATTERNS.md`.

**Manifest update:** After the initial map, OmegaP46ContractRework supplied its report-only proposed writer manifest. The exact ownership excerpt was read at `agent://OmegaP46ContractRework:748–826`; it identifies proposed SEC-NET 1.1.0, two five-path implementation writers and a four-path documentation writer. The manifest is now classified below. It is **not an observed source change, approved GSD plan or accepted design**. Only this manifest excerpt, not the complete revised API/confinement contract, was consumed by the mapper.

The A01 route supplies scope/ownership and a selected alternative for A03 to specify; it does not approve confinement. Main alone must capture, compute the actual hash of and pin the genuinely accepted complete revised result. The route and peer identify `local://Tutmu-p46-contract.revised.result.json` as the intended capture. This mapping does not supply or fabricate its digest, acceptance or complete contents. The planner must use the later **complete exact hashed capture** and applicable authentic review/security outcomes before fixing new interfaces or releasing writers. **SEC-NET1.0.0 is not an accepted design or copy source here.**

Product-content reads were bounded to `webpack.py`, `playwright_browser.py`, `mcp_server.py`, `policy.py`, and `test_web.py`. All five analogs were confirmed git-tracked. Additional manifest paths were checked only through explicit-path Git tracking and exact-name filesystem metadata; their source/document contents were not opened. No install/runtime mirror, unbounded scan, CLAUDE/AGENTS/context-file search or reference-clone inspection was used.

The mapper made no product/docs/config edit, check, install, public-network access, credential access or Git mutation. Its sole repository output is this PATTERNS file. Preserve historical 46-01/48-01 plans and summaries, the original dirty Phase52 work, existing repository/branch, Python/pip/MIT and the single agent-process boundary. New work belongs only in focused `gap_closure: true` plans. Main owns union verification/publication; Railway remains connect/prepare only. Real Python 3.12/3.13/3.14 and matching-head CI acceptance remains required, not supplied here.

## File Classification

These are **proposed** writer targets, not authorization to edit them. “Existing” is supported by explicit-path `git ls-files`; “proposed creation” is supported by no tracking entry plus the exact-path lookup reporting it missing. Match quality refers to available **style**, never to a completed secure implementation.

| Proposed New/Modified File | State / Proposed Owner | Role | Data Flow | Closest Inspected Analog | Match Quality |
|---|---|---|---|---|---|
| `omes/providers/destination.py` | Proposed creation; Phase46FetchIntegration | provider; model; transport utility | request-response; address/response transform | `omes/tools/webpack.py` imports, `WebContext`, `_error`, preview boundary | partial style; no safe-connection core analog |
| `omes/tools/webpack.py` | Existing tracked; Phase46FetchIntegration | service; context model; registry adapter | request-response; transform; screenshot file-I/O | Same file: `WebContext`, `preview_check`, `review_page`, registration | exact style; vulnerable internals are cutover seams |
| `omes/mcp_server.py` | Existing tracked; Phase46FetchIntegration | provider/composition root; MCP controller | request-response; schema/result transform | Same file: `default_registry`, `main`, `call_tool_handler` | exact composition/result style |
| `omes/tests/test_web.py` | Existing tracked; Phase46FetchIntegration | test | request-response; injected lifecycle; temporary file-I/O | Same file: `_ctx`, preview/review/approval assertions | exact unit-test style; not runtime safety proof |
| `omes/tests/test_mcp_server.py` | Existing tracked; Phase46FetchIntegration; body unread | test | request-response; dispatch/result transform | `omes/tests/test_web.py` registry/approval assertions; `mcp_server.py` observed result boundary | role-match; MCP-specific test conventions uninspected |
| `omes/tools/playwright_browser.py` | Existing tracked; Phase46BrowserSafety | service/browser provider | request-response; event-driven lifecycle; file-I/O | Same file: injected launcher and lifecycle methods | exact adapter style; no mandatory confinement analog |
| `omes/tools/browser_egress.py` | Proposed creation; Phase46BrowserSafety | provider; enforcement/lifecycle utility | event-driven; request-response; descriptor/process lifecycle | `omes/tools/playwright_browser.py` explicit resource ownership/cleanup | role-match only; kernel/IPC/event machinery has no inspected analog |
| `omes/tools/browser.py` | Existing tracked; Phase46BrowserSafety; body unread | service/registry adapter [INFERENCE from manifest's in-zone browser migration] | request-response; browser lifecycle [INFERENCE] | `omes/tools/webpack.py` family registration; `playwright_browser.py` public lifecycle shapes | role-match; actual wrapper signatures uninspected |
| `omes/tests/test_platform.py` | Existing tracked; Phase46BrowserSafety; body unread | test | request-response; browser lifecycle/file-I/O [manifest-driven classification] | `omes/tests/test_web.py` browser lifecycle/resource assertions | role-match; unrelated platform behavior must remain untouched |
| `omes/tests/test_browser_egress.py` | Proposed creation; Phase46BrowserSafety | test | event-driven; request-response; confinement/descriptor lifecycle | `omes/tests/test_web.py` fixture injection and explicit close/resource assertions | role-match; no real confinement-fixture analog |
| `docs/tool-host.md` | Existing tracked; Phase46Docs; body unread | documentation / operator contract | batch; implementation/evidence transform | No inspected documentation-style analog; observed `mcp_server.py` wiring supplies facts only | no source-pattern analog in allowed reads |
| `docs/architecture.md` | Existing tracked; Phase46Docs; body unread | documentation / architecture contract | batch; implementation/evidence transform | No inspected documentation-style analog; observed context/policy/lifecycle seams supply facts only | no source-pattern analog in allowed reads |
| `SECURITY.md` | Existing tracked; Phase46Docs; body unread | documentation / security contract | batch; accepted-security-evidence transform | No inspected documentation-style analog; supplied before receipts and observed unsafe seams are evidence only | no source-pattern analog in allowed reads |
| `CHANGELOG.md` | Existing tracked; Phase46Docs; body unread | documentation / change record | batch; verified-change transform | No inspected changelog-style analog | no source-pattern analog in allowed reads |

**Intentionally unchanged reference:** `omes/policy/policy.py` is an existing tracked model/utility (`file-I/O` and declarative decision transform), with an exact self-analog in `SeatPolicy.__init__/load/allows_host` and `_check`. It is not in either proposed code-writer manifest. Its presence in the A01 analysis scope does not authorize assigning a new policy writer. Reuse its public exact/empty semantics through composition; the mapper does not propose changing its schema/private fields.

### Proposed ownership and dependency boundaries

- **Phase46FetchIntegration:** exactly `omes/providers/destination.py`, `omes/tools/webpack.py`, `omes/mcp_server.py`, `omes/tests/test_web.py`, `omes/tests/test_mcp_server.py`. Sole shared transport/webpack/MCP composition writer; its two tests are exclusive. The report proposes publishing the shared definitions before coupled browser implementation, then integrating the completed browser handoff.
- **Phase46BrowserSafety:** exactly `omes/tools/playwright_browser.py`, `omes/tools/browser_egress.py`, `omes/tools/browser.py`, `omes/tests/test_platform.py`, `omes/tests/test_browser_egress.py`. No destination/webpack/MCP or their-test writes. Guarded factory/terminal composition is handed back to the shared writer, not implemented through sibling edits.
- **Phase46Docs:** exactly `docs/tool-host.md`, `docs/architecture.md`, `SECURITY.md`, `CHANGELOG.md`. Report proposes documentation after both code writers stop and Main supplies actual candidate-bound receipts/accepted disposition. No canonical `.planning` ownership is assigned to this writer.
- `46-VERIFICATION.md` remains a parent-owned planning/evidence record named by the route. The route also names `46-SECURITY.md` for independent security reporting; verification describes `46-VALIDATION.md` as partial. These are evidence records, not product-source analogs or additional mapper outputs.
- These manifests remain proposals until Main pins the accepted exact capture and focused plan/ownership. No source API, task lease, runtime pass or dispatch is asserted by this mapping.

## Pattern Assignments

### `omes/providers/destination.py` — proposed transport provider/models

**State:** Proposed new file; exact-path lookup reported it missing. **Analog:** `omes/tools/webpack.py`, partial construction/import/response-boundary style only.

**Imports pattern — `webpack.py:12–27`:** stdlib first and package-absolute collaborator imports. Reuse organization, not every legacy dependency.

```python
import contextlib
import hashlib
import ipaddress
import re
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from omes.credentials.redact import redact_text
from omes.tools.playwright_browser import PlaywrightBrowser
from omes.tools.registry import ToolRegistry
from omes.tools.vision import vision_analyze
```

`urllib.request` is an observed legacy import, not a required safe-transport dependency. `WebContext`'s dataclass excerpt below and `SeatPolicy`'s validated-construction excerpt under Shared Patterns supply existing plain-model conventions. The `_error` excerpt supplies the adapter-facing error dictionary convention; it does not define the proposed transport's internal error/type protocol.

**Core/security limit:** No all-address admission, numeric dialer, one-use authority/permit, actual-peer/TLS or duplicate-preserving exchange implementation is observed in the five source bodies. Do not copy `_default_fetch` as the secure core. New definitions, ownership/cleanup, response-byte/header semantics and their exact signatures must come from the complete accepted hashed revision. This assignment does not invent them.

**Testing assignment:** Proposed owner authors transport/HTTP/public-shape/composition tests in its exclusively owned `test_web.py` and `test_mcp_server.py`; use their inspected analogs below. The mapper does not execute tests or infer an additional provider test filename.

---

### `omes/tools/webpack.py` — existing service/context/registry adapter

**Analog:** Current tracked file itself; preserve family conventions/public result boundary, replacing vulnerable internals.

**Trusted construction/injection — lines 124–134:**

```python
@dataclass
class WebContext:
    """Everything the web tools need. Clients default to unconfigured."""

    root: str | Path = "."
    vercel: Any = None
    fetch: Any = None
    browser_factory: Any = None
    vision: Any = None
    artifacts_dir: str | Path = "artifacts/reviews"
    allowed_hosts: tuple[str, ...] | None = None
```

Injection happens through Python construction, separate from tool arguments. Observed current call shapes are `fetch(url, timeout)` returning a dictionary and `browser_factory()` returning the browser adapter. These `Any` seams establish no observed authority guarantee. The later contract supplies replacement interfaces; no new safety keyword/type is asserted to exist here.

**Validation, refusal, fetch seam and outward result — lines 218–250:**

```python
    def preview_check(self, url: str, expect_status: int = 200) -> dict[str, Any]:
        """Fetch one URL: status, latency, content hash, redirect. No redirects followed."""
        if not isinstance(url, str) or url.strip() == "":
            raise ValueError("url must be a non-empty string")
        if isinstance(expect_status, bool) or not isinstance(expect_status, int):
            raise ValueError("expect_status must be an integer")
        blocked = _check_url(url, self.ctx.allowed_hosts)
        if blocked is not None:
            return {"url": url, "error": blocked}
        host = urlparse(url).hostname or ""
        fetch = self.ctx.fetch or _default_fetch
        result = fetch(url, FETCH_TIMEOUT)
        if not isinstance(result, dict) or result.get("error"):
            return (
                result
                if isinstance(result, dict)
                else {"error": "upstream_error: no object"}
            )
        body = result.get("body", b"")
        if isinstance(body, str):
            body = body.encode("utf-8")
        return {
            "url": url,
            "host": host,
            "status": result.get("status"),
            "expected": expect_status,
            "matches": result.get("status") == expect_status,
            "ms": result.get("ms"),
            "content_type": (result.get("headers") or {}).get("content-type"),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "redirect": (result.get("headers") or {}).get("location"),
        }
```

**Unsafe legacy host-list branch — lines 90–95; do not copy as remediated policy:**

```python
    if allowed_hosts is not None and not any(
        host == allowed.lower() or host.endswith("." + allowed.lower())
        for allowed in allowed_hosts
    ):
        return f"forbidden_host: {host} is not in the fetch allowlist"
    return None
```

This admits subdomains and treats `None` differently from an empty tuple, unlike `SeatPolicy.allows_host`. `_check_url:58–95` examines URL spelling/literal addresses, not DNS answers or the connected peer; no endpoint-port admission or HTTPS peer-binding mechanism is observed. These are cutover defects, not secure analogs.

**No-follow seam — lines 117–121:**

```python
class NoRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so the report shows the original response."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
```

Retain the fetch no-follow requirement, not the unchecked connection. `_default_fetch:98–114` uses `build_opener(NoRedirects)`, reads up to 2,000,000 bytes, flattens response headers into a dictionary and catches exceptions as `upstream_error`. It establishes no all-address/actual-peer/proxy/TLS binding. The hook alone is not runtime proof of status-specific redirect reporting. Do not extend the preview byte bound/header dictionary to truncate browser resources or flatten duplicate `Set-Cookie`.

**Review seams:** `review_page:281–337` probes first, chooses `self.ctx.browser_factory or PlaywrightBrowser` at 294–295, checks start/navigation/screenshot error dictionaries, then invokes vision. Terminal suppression is extracted under Shared Patterns. `_safe_shot_name:48–55` and the invalid-name branch at 311–318 supply screenshot-path validation, not network confinement. Keep the existing registration/approval and error conventions below. Corresponding test source: `test_web.py:144–166,183–209`.

---

### `omes/mcp_server.py` — existing composition root/MCP controller

**Analog:** Current `default_registry`/`main` wiring and MCP result translation.

**Observed imports — line 25 and line 48, respectively:**

```python
from omes.policy.policy import SeatPolicy
```

```python
from omes.tools.webpack import WebClient, WebContext, register_web_tools
```

**Current construction signature — lines 115–122:**

```python
def default_registry(
    root: str | Path,
    home: str | Path,
    *,
    policy: Any = None,
    approval_log: Any = None,
    env: dict | None = None,
) -> ToolRegistry:
```

**Policy/registry composition — lines 134–138:**

```python
    env = dict(env or {})
    registry = ToolRegistry(approval_log=approval_log, policy=policy)
    root = Path(root)
    home = Path(home)
    register_coding_tools(registry, root / "omes", policy=policy)
```

**Web construction — line 161:**

```python
    register_web_tools(registry, WebClient(WebContext(root=root)))
```

Policy reaches registry/coding construction, but the web context receives **only `root`**. Passing policy to `ToolRegistry` is not observed transport enforcement. This is the sole shared-writer seam for binding both trusted network consumers to the later exact policy authority/worker lifecycle. No safe-transport/browser injection keywords exist in the observed signature.

**Fail-closed policy load — lines 291–295:**

```python
    try:
        policy = SeatPolicy.load(root / "omes" / "contracts" / "policies" / "omes.json")
    except (OSError, ValueError) as exc:
        print(f"omes-mcp-server: cannot load seat policy: {exc}", file=sys.stderr)
        return 2
```

`main:312–314` passes this policy and approval log into construction. Retain trusted load/failure behavior; do not turn malformed/empty policy into unrestricted defaults or invent an env/config schema here.

**Roster guard/result translation — lines 228–241:**

```python
        if allowed is not None and params.name not in allowed:
            payload = json.dumps(
                {"error": f"policy forbids {params.name}", "tool": params.name}
            )
        else:
            payload = registry.dispatch(params.name, params.arguments or {})
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = {"output": payload}
        is_error = isinstance(decoded, dict) and "error" in decoded
        return CallToolResult(
            content=[TextContent(type="text", text=payload)], is_error=is_error
        )
```

Keep refusal visible at the top-level `error`/`is_error` boundary. The inspected async handler directly calls dispatch; no worker/cancellation-drain API is observed. Use the accepted revision for sync Playwright creation/use/close, serialization and terminal cancellation behavior, not a second MCP convention. Imported registry/approval implementations were not read.

---

### `omes/tests/test_web.py` — existing FetchIntegration regression surface

**Analog:** Current tracked test itself. Proposed manifest gives this file exclusively to FetchIntegration.

**Imports — lines 3–13:**

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from omes.tools.approvals import ApprovalLog
from omes.tools.playwright_browser import PlaywrightBrowser
from omes.tools.registry import ToolRegistry
from omes.tools.webpack import WebClient, WebContext, register_web_tools
```

**Preview fake result — lines 54–60:**

```python
def _fetch_ok(url, timeout):
    return {
        "status": 200,
        "headers": {"content-type": "text/html"},
        "body": b"<h1>hi</h1>",
        "ms": 12.5,
    }
```

This is a preview/unit seam, not the future duplicate-preserving browser exchange or real-peer evidence.

**Per-test overrides — lines 107–119:**

```python
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
```

Reuse pytest functions, `tmp_path`, scoped construction overrides and owned fakes rather than operator/global state. Migrate these callers to the accepted interfaces if changed; a fake launcher must not become an unguarded production bypass.

**Visible result assertions — lines 144–150:**

```python
def test_preview_shape_mismatch_and_failure(tmp_path):
    client = WebClient(_ctx(tmp_path))
    ok = client.preview_check("https://acme.test/", expect_status=200)
    assert ok["matches"] is True and ok["status"] == 200 and ok["bytes"] == 11
    assert ok["host"] == "acme.test" and ok["redirect"] is None
    mismatch = client.preview_check("https://acme.test/", expect_status=201)
    assert mismatch["matches"] is False
```

The injected failure case is at 151–157. The existing review test at 183–209 asserts connectivity, page title/final URL/status, screenshot path/file, vision answer, connectivity failure and invalid-name refusal. Preserve these public outcomes rather than narrowing to construction/import tests.

**Validation/refusal assertions — lines 158–166:**

```python
    with pytest.raises(ValueError, match="non-empty string"):
        client.preview_check("")
    assert "only http" in client.preview_check("file:///etc/passwd")["error"]
    assert "forbidden_host" in client.preview_check("http://localhost:9/")["error"]
    assert "forbidden_host" in client.preview_check("http://169.254.169.254/")["error"]
    assert "forbidden_host" in client.preview_check("http://10.0.0.9/")["error"]
    scoped = WebClient(_ctx(tmp_path, allowed_hosts=("acme.test",)))
    assert scoped.preview_check("https://acme.test/")["matches"] is True
    assert "allowlist" in scoped.preview_check("https://other.test/")["error"]
```

These fake-fetch tests do not exercise DNS/mixed answers, numeric aliases, peer mismatch, TLS or default-registry `SeatPolicy` composition. The accepted plan must add those obligations without claiming this existing unit coverage already closes the gap.

---

### `omes/tests/test_mcp_server.py` — existing, unread MCP test target

**Analog:** `omes/tests/test_web.py:231–253` for registry construction/JSON outcome/approval style; `omes/mcp_server.py:228–241` for the actual observed MCP error boundary. This target is tracked but its contents were not read; no fixture/function names in it are asserted.

**Concrete dispatch assertion — `test_web.py:241–244`:**

```python
    for tool in ("web_vercel_promote", "web_vercel_rollback"):
        assert json.loads(
            registry.dispatch(tool, {"project": "acme", "deployment_id": "d-1"})
        ) == {"error": "approval required", "tool": tool}
```

Use the imports and scoped construction pattern from `test_web.py:3–13,107–119`; preserve tool/approval behavior. MCP assertions must additionally preserve `CallToolResult.is_error`, policy-bound default construction and the accepted same-worker/cancellation terminal protocol. No existing async/MCP-test fixture is inspected here, so do not invent one or claim source-only tests are runtime concurrency evidence.

---

### `omes/tools/playwright_browser.py` — existing BrowserSafety adapter

**Analog:** Current tracked file for public methods/results and ownership style only.

**Imports — lines 11–13:**

```python
from collections.abc import Callable
from pathlib import Path
from typing import Any
```

**Current injection — lines 27–31:**

```python
    def __init__(self, launch: Callable[[], Any] | None = None) -> None:
        self._launch = launch or _default_launch
        self._handle: Any = None
        self._browser: Any = None
        self._page: Any = None
```

**Startup shape — lines 33–43; not a guarded-startup implementation:**

```python
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
```

The default at 16–21 directly starts sync Playwright/headless Chromium. Tuple-or-bare-browser acceptance and raw default fallback are cutover seams, not authority/confinement proof. The exact accepted launch/session protocol must install enforcement and target observation before first-page/descendant traffic; do not preserve a raw-launch fallback.

**Navigation success/error shape — lines 51–59:**

```python
        try:
            response = self._page.goto(url, wait_until="domcontentloaded")
            return {
                "title": self._page.title(),
                "url": self._page.url,
                "status": response.status if response is not None else None,
            }
        except Exception as exc:
            return {"error": f"navigate failed: {exc}"}
```

Not-started/empty-URL guards are at 47–50. `snapshot:61–68` and `screenshot:70–80` supply title/URL and path/byte-count dictionaries or errors. Success here is not evidence of every-request enforcement or absence of late/handled denial.

**Explicit resource cleanup — lines 82–96:**

```python
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
```

Reuse explicit ownership/reset/attempt-all/error aggregation, but it is not a descendant/event-drain/cancellation/sticky-refusal implementation. The accepted revision must define those semantics and authority; do not infer a safety-event API from this adapter. Browser lifecycle testing style appears below.

---

### `omes/tools/browser_egress.py` — proposed enforcement owner/controller

**State:** Proposed creation, missing at exact lookup. **Analog:** `playwright_browser.py:27–43,82–96`, role-match only.

The imports (`playwright_browser.py:11–13`) and the complete close excerpt above demonstrate the existing small provider/owned-resource convention. `webpack.py:41–42,361–365` supplies adapter-facing error formatting; `SeatPolicy` below supplies trusted decision semantics. Do not copy permissive startup, ordinary `goto` success or exception suppression as enforcement.

There is **no inspected core analog** for the revised namespace/IPC/descriptor boundary, trusted event ownership, before-traffic target attachment, native exchange or terminal descendant/event barrier. Implement their exact definitions only from Main's complete accepted hashed contract; this mapping proposes no syscall profile, protocol API, control FD or observer. Planned browser capabilities must hand off to the sole shared writer without editing its files. New code does not authorize a new agent/public proxy/unguarded launch or installer activity.

**Testing:** Proposed exclusive `test_browser_egress.py` and bounded browser changes in `test_platform.py`. Existing fake close tests supply style only; actual confinement/every-path proof belongs to Main after all writers stop.

---

### `omes/tools/browser.py` — existing, unread browser family seam

**Analog:** `webpack.py:358–396` for single-family handler/schema/error/approval registration and `playwright_browser.py:33–96` for observed browser result/lifecycle shapes.

Tracking/exact manifest establishes this is an existing target, but its own imports, functions and public signatures were not inspected. Its role/data-flow classification is inferred from the report's in-zone browser migration. Do not assert it already accepts any revised factory/session parameter or copy speculative wrappers.

Use the concrete `_wrap`/registration excerpts under Shared Patterns as the closest allowed family convention. The actual executor must migrate this target's in-zone unchecked callers to the accepted lifecycle, preserve existing public behavior and not create a parallel registration/approval convention. This mapper cannot enumerate its internal callers under the bounded read contract. No unrelated unconfigured platform integrations are added.

---

### `omes/tests/test_platform.py` — existing, unread BrowserSafety compatibility target

**Analog:** `omes/tests/test_web.py:212–228`, role-match for browser lifecycle/resource assertions. The target's own test body/fixtures were not read.

**Concrete lifecycle assertion style:**

```python
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
```

Reuse explicit holder/resource state and repeated-close assertions, with the actual accepted new protocol. Keep unrelated platform tests/behavior unchanged. This fake fixture does not establish new authority, every-request confinement or real descendant cleanup. The observed `FakePage.screenshot` at `test_web.py:76–78` writes `b"\x89PNG-fake"`; file existence/nine bytes are not real PNG proof.

---

### `omes/tests/test_browser_egress.py` — proposed browser enforcement regressions

**State:** Proposed creation, missing at exact lookup. **Analog:** `test_web.py:3–13,107–119,212–228` for pytest imports, scoped injection and explicit lifecycle/resource outcomes; role-match only.

Copy those exact style excerpts, not fake-browser evidence claims. The accepted contract supplies the real descriptor/namespace/notification/target/HTTP fixture protocol and expected terminal outcomes; none exists in the inspected unit-test source. Distinguish trusted protocol-unit tests from genuine installed guarded-Chromium observations.

Required behavioral assertions must observe a successfully admitted initial public document, zero forbidden target requests, sticky refusal through operations/close and zero vision invocations. Cover partial start, late/handled refusal, observer/owner failure, cleanup/cancellation, new-target/redirect races and positive native HTTP/TLS/rendering semantics under the same enforcement. The shared writer owns review/MCP composition tests, so this browser file does not acquire writes to `test_web.py` or `test_mcp_server.py`.

---

### Documentation targets — proposed Phase46Docs follow-through

No documentation body was inspected, so no existing heading/changelog formatting convention can be claimed or quoted. These four tracked files are individually classified and intentionally have **no source-pattern assignment**. Their writer must inspect their actual current conventions under its own bounded assignment after code/evidence prerequisites; this mapper must not widen its reads.

- **`docs/tool-host.md`** (documentation, batch/evidence transform): observed facts come from `mcp_server.py:115–138,161,228–241,291–295,312–314`. Document the implemented policy-bound construction, supported prerequisites and public refusal/MCP behavior only after actual implementation. Do not describe the legacy root-only context as guarded or claim a new config knob exists from this map.
- **`docs/architecture.md`** (documentation, batch/evidence transform): observed construction/lifecycle facts come from `webpack.py:124–134,281–337`, `playwright_browser.py:27–96` and `policy.py:22–32,68–72`. Describe only the later implemented single-agent/optional browser subprocess and actual authority/terminal boundary, not a proposed report as shipped architecture.
- **`SECURITY.md`** (documentation, accepted-evidence transform): supplied before receipts and `46-VERIFICATION.md` identify the two real gaps. After-fix claims must cite Main's actual accepted candidate-bound negative and positive receipts, exact enforcement limits and unsupported prerequisites. No source-only, design-grade or matrix claim substitutes for runtime security acceptance.
- **`CHANGELOG.md`** (documentation, verified-change transform): list the actually implemented fetch/browser/policy-composition behavior and public compatibility; no unexecuted support/security/CI success claim. Current changelog formatting was not read and must not be invented.

## Shared Patterns

### Public policy methods and exact/empty network semantics

**Source:** The intentionally unchanged tracked `omes/policy/policy.py`.

**Validated construction — lines 22–32:**

```python
    def __init__(self, document: dict) -> None:
        _check(document)
        self._document = document
        tools = document.get("tools") or {}
        allow = tools.get("allow")
        self._allow_all = allow is None
        self._allowed = frozenset(allow) if isinstance(allow, list) else frozenset()
        paths = document.get("paths") or {}
        self._read_only = tuple(paths.get("read_only") or ())
        network = document.get("network") or {}
        self._hosts = frozenset(host.lower() for host in (network.get("hosts") or ()))
```

**Host decision — lines 68–72:**

```python
    def allows_host(self, host: str) -> bool:
        """Exact allowlist match, case-insensitive. No implied subdomains."""
        if not isinstance(host, str) or host == "":
            return False
        return host.lower() in self._hosts
```

**Network document validation — lines 123–130:**

```python
    network = document.get("network", {})
    if not isinstance(network, dict):
        raise ValueError("policy network must be an object")
    hosts = network.get("hosts", [])
    if not isinstance(hosts, list) or any(
        not isinstance(host, str) or host == "" for host in hosts
    ):
        raise ValueError("policy network.hosts must be a list of hosts")
```

`load:34–46` raises for absent/malformed policy and requires a JSON object; `_check:103–130` validates schema/field types. Imports at 10–14 use future annotations, stdlib JSON/regex and pathlib. The class's line-20 convention is to ask public `allows_*` methods, not raw fields.

**Apply to:** Both consumers and trusted default MCP composition. Exact case-insensitive host match and empty/missing network-host denial are the safe existing policy analog. Missing `tools.allow` permits tools, a deliberately different rule that must not be copied to network admission. Do not coerce an empty host policy to unrestricted `None`, infer subdomains or edit private fields/schema. Host-policy matching does not itself validate DNS, endpoint ports, peers or TLS.

Registry/tool/approval authorization and destination/connection admission are separate layers. Trusted capabilities stay in Python construction, not model-supplied flags. The observed `fetch or _default_fetch`, `browser_factory or PlaywrightBrowser` and `launch or _default_launch` fallbacks are cutover seams; do not retain unguarded alternate paths/shims in the remediated composition.

### Existing error dictionary, family registration and approval boundary

**`webpack.py:41–42`:**

```python
def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}
```

**Argument wrapper — `webpack.py:361–365`:**

```python
    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}
```

**Registration/approval — `webpack.py:388–396`:**

```python
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=name in ("web_vercel_promote", "web_vercel_rollback"),
        )
    return list(WEB_TOOL_NAMES)
```

**Apply to:** New transport-to-web adapter, existing web/browser family callers and MCP error translation. Keep the six web tool names/schema boundary and existing promote/rollback approval classifications. Observed handlers/schemas at 367–460 expose no transport/launcher injection as tool arguments. Refusal must remain visible as an error, not a successful screenshot/report with a nested warning. Imported registry/approval internals are uninspected; claims here are limited to observed callsites/tests. The SSRF task authorizes no deployment mutation.

### Terminal refusal and vision boundary

**Unsafe current seam — `webpack.py:327–337`; identify the defect, do not copy suppression:**

```python
        finally:
            with contextlib.suppress(Exception):
                browser.close()
        vision = vision_analyze(self.ctx.vision, shot["path"], question)
        return {
            "url": url,
            "connectivity": connectivity,
            "page": navigated,
            "screenshot": shot,
            "vision": vision,
        }
```

The `finally` scope gives useful ownership structure, but suppressed exceptions/ignored close results are not a terminal security barrier. Only the complete accepted contract may define admission stop, pending mediation/enforcement drain, retained first refusal, descendant completion, partial-start/cancellation handling and the immutable close/terminal handoff. No such API or trusted denial producer is observed in the five existing source bodies. The shared writer must gate clean review/vision on that actual terminal decision; BrowserSafety hands it back without touching shared files.

### Behavioral evidence: preserve both real before/after pairs

**Sources:** `test_web.py:54–119,144–166,183–253`; supplied `local://omega-security-before.md`; scoped route/rework feedback.

Reuse scoped pytest collaborator injection, visible outcome/resource assertions and real server-observed behavior where the accepted fixture contract requires it. Existing fake fetch/browser tests are not proof of private-peer refusal, real PNGs or mandatory confinement. No real DNS/TLS/namespace/descriptor fixture convention was inspected.

The supplied Main receipts already establish two distinct **before** failures; neither is replayed by this role:

1. **Fetch:** actual `_check_url`/`_default_fetch`, allowed `omega-rebind.example` resolving to loopback, HTTP 200, fixture request `/private-probe`. Matched after obligation: refusal and `private_server_requests=[]` before the private server receives a request.
2. **Browser:** actual legacy `PlaywrightBrowser.start/navigate/snapshot/close` with installed Chromium, an admitted synthetic public fixture, then private meta-navigation reaching `/private-browser-probe`. Matched after obligation: actual guarded Chromium admits the initial public page, refuses the later private navigation before any fixture request, retains refusal through terminal cleanup and never invokes vision. Initial-page denial, `not_configured`, fake Chromium or initial-probe failure does not satisfy this pair.

Main's later union must cover all-address/mixed A/AAAA, ambiguous numeric forms, exact/empty endpoint policy, actual peer/original-host HTTPS/SNI, proxy bypass exclusion and fetch no-follow **301/302/303/307/308**. Browser coverage must independently address redirects, frames/resources/scripts, XHR/fetch, meta navigation, popup/worker/new-target ordering, subsequent navigation, alternate channels, retained descriptors/IPC, descendant confinement, late/handled denial and cleanup/cancellation. Positive cases must measure real non-GET/body, cookies/repeated `Set-Cookie`, encoded resources, native redirect method/final URL/origin/CORS, verified HTTPS, real PNG and cleanup **under the same enforcement**. This is a parent evidence obligation drawn from scoped inputs, not executed proof or a mapper-authored mechanism.

## No Analog Found

### Uninspected documentation conventions

| File | Role / Flow | Reason |
|---|---|---|
| `docs/tool-host.md` | documentation; batch/evidence transform | Existing tracked target, but document bodies are outside this mapper's permitted reads. No heading/operator-guide convention asserted. |
| `docs/architecture.md` | documentation; batch/evidence transform | Existing tracked target; source seams provide facts, not a inspected architecture-document template. |
| `SECURITY.md` | documentation; accepted-evidence transform | Existing tracked target; actual before receipts are evidence, not its unread disclosure/support format. |
| `CHANGELOG.md` | documentation; verified-change transform | Existing tracked target; current entry/version format uninspected. |

“No analog” here is a bounded-read limit, not a claim the repository lacks documentation conventions. The later documentation writer must reuse them under its own assignment.

### Required security cores without an implemented bounded-source precedent

- `omes/providers/destination.py` / the legacy fetch cutover: no observed safe resolver/admission/permit/numeric peer/TLS/exchange core; only partial model/adapter style.
- `omes/tools/browser_egress.py` / `playwright_browser.py`: no observed mandatory confinement, trusted sticky event producer, before-traffic attachment or terminal descendant/drain implementation; lifecycle style alone is insufficient.
- MCP shared composition: current root-only web context does not implement policy-bound safe consumers or serialized cancellation drain.
- New/existing gap tests: no observed real DNS/peer/TLS or confined-Chromium fixture. Fake methods/PNG and close flags must not masquerade as the required actual after evidence.

Use Main's later complete exact accepted hashed revision for these cores, not absent RESEARCH, rejected SEC-NET1.0.0, speculative new APIs or unsafe urllib/Playwright fallback.

## Metadata

**Strong analog search scope:** Exactly `omes/tools/webpack.py`, `omes/tools/playwright_browser.py`, `omes/mcp_server.py`, `omes/policy/policy.py`, `omes/tests/test_web.py`. Five strong tracked analogs were read; search stopped there. No assertion that uninspected modules contain no other patterns/callers.

**Source-content scans:** 5 files, 1,270 lines total, each read in one bounded ranged call. Targeted grep anchors supplied citation line numbers; no second source-range read occurred.

**Manifest-only reads:** Peer report excerpt `agent://OmegaP46ContractRework:748–826` supplied exact proposed paths/ownership. Explicit-path `git ls-files` confirmed seven existing code/test writer targets, four existing documentation targets and the separate policy reference. Exact-name glob reported `destination.py`, `browser_egress.py`, `test_browser_egress.py` missing and `CHANGELOG.md` present; a separate explicit tracking call confirmed the changelog. No additional target bodies were read. The phase lookup was limited to `*RESEARCH.md` and this output path.

**Source snapshot fingerprints:** These identify the initial read-only source snapshot, not the pending revised-contract digest or runtime/security evidence.

| Source | Lines | SHA-256 |
|---|---:|---|
| `omes/tools/webpack.py` | 465 | `c077a5f2966b159081b6c604feb270c6168a866cee2d83a357d8e214005fd31d` |
| `omes/tools/playwright_browser.py` | 99 | `a3d30f084c58807e79d0af11fb69022fcaf5fa55636cbd3c7cda5581e72bdd24` |
| `omes/mcp_server.py` | 320 | `efc8bec843b1bfb32f119676ed018b289041e37d56f4e9e098a6c63d91820ba4` |
| `omes/policy/policy.py` | 133 | `d8f241c77018c4bb95fccf1534afb0b70dec7d2f1436b85bfe7d216529c87b23` |
| `omes/tests/test_web.py` | 253 | `9b0f414dddb97fab1c10c403b55cec88617ef6ac976a697871a84ed11dd94d4b` |

**Unread limits:** Bodies of `browser.py`, `test_mcp_server.py`, `test_platform.py`, all four documentation targets, registry/approvals/vision, other tests, installed Playwright/Chromium internals, deployment configuration and reference clones. The complete revised API/confinement report was not consumed/pinned/accepted by this mapper. Manifest role inferences are marked; imported names do not prove unseen implementations.

**Runtime limits:** Only bounded control/source reads, source anchors, explicit tracking/name/line-count/fingerprint metadata and the PATTERNS write were exercised. No tests/evals/lint/format/build/smoke, browser/confinement probe, install, CI/gate execution or pre-fix replay. Historical green verification remains historical and closes neither security gap nor the real interpreter matrix. No product, documentation, config, tracker or historical-plan write was performed.

## PATTERN MAPPING COMPLETE

The actual returned report's 14 proposed write targets are classified and distinguished from the unchanged policy reference, existing tracked files and three proposed creations. Ten code/test targets have bounded source-style assignments using five strong tracked analogs; four unread documentation targets and the novel security cores have explicit limits. The planner must still pin Main's later complete exact hashed revised-contract capture and genuine acceptance/ownership before specifying executable new APIs or coupled implementation plans.
