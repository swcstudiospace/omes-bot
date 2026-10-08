---
phase: "46"
slug: "land-hardening"
status: blocked
threats_open: 2
threats_total: 12
threats_closed: 10
asvs_level: 1
block_on: high
register_authored_at_plan_time: false
created: "2026-10-07"
---

# Phase 46 — Security

## Trust Boundaries

tool arguments → network/database/resource IDs; external/nested values → events/recall; filenames → screenshots; model actions → approvals; stale queue/plan state → work selection.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-46-01 | Information disclosure | Nested credential values in lead events/recall | high | mitigate | `omega_prime/credentials/redact.py:45-55` recursively redacts string values; `omega_prime/tools/lead.py:264-270,378-408,600-626` calls it at mirror/recall/outgoing-event boundaries. `omega_prime/tests/test_lead.py:335-358` checks nested supported-token removal in both stored and emitted payloads; `omega_prime/tests/test_credentials.py:84-91` checks supported patterns. | closed, L1 |
| T-46-02 | Tampering / Repudiation | Intake leases and persisted claim state | medium | mitigate | `omega_prime/tools/lead.py:96-156` records claim time, releases/reclaims stale in-progress work; `192-197` writes temporary state then replaces atomically. `omega_prime/tests/test_lead.py:109-160` covers no premature reclaim, expiry reclaim, release, and missing ID. Closure is lifecycle/persistence presence, not cross-process concurrency certification. | closed, L1 |
| T-46-03 | Information disclosure / Tampering | Railway deployment-service binding | high | mitigate | `omega_prime/tools/infra.py:134-174,333-365` resolves service before logs, checks older IDs, and refuses a client without lookup. `omega_prime/tests/test_infra.py:126-157` covers latest/older IDs, cross-service/project refusal, missing ID, and lookup-less refusal. Shipped host leaves this external client unconfigured (`omega_prime/mcp_server.py:163`). | closed, L1 |
| T-46-04 | Tampering | Play merge / App Store app disambiguation | high | mitigate | `omega_prime/tools/mobile.py:170-200` preserves other version releases before updating; `339-357,390-410` scopes by app ID and refuses multiple matching versions. `omega_prime/tests/test_mobile.py:143-174,214-235` checks merge and ambiguous/scoped flows. No live store actions claimed. | closed, L1 |
| T-46-05 | Spoofing / Elevation of privilege | Receipt identity and proposal acknowledgment coverage | high | mitigate | `omega_prime/tools/quality.py:225-255` requires an author bot, refuses self-approval, and validates receipt; `316-351,433-458` parses the fixed-shape consumer list and reports missing/rejected acknowledgments. `omega_prime/tests/test_quality.py:122-139,169-202` covers anonymous/self/bad receipts and JSON/YAML required-consumer coverage. | closed, L1 |
| T-46-06 | Tampering / Repudiation | Truncated scan falsely clean | medium | mitigate | `omega_prime/tools/quality.py:389-429` records truncation and sets `ok = not findings and not truncated`. `omega_prime/tests/test_quality.py:220-249` covers clean/secret files and generated-directory exclusion. The >2000-file branch is source evidence, not a personally exercised or dedicated-test claim. | closed, L1 |
| T-46-07 | Tampering / Elevation of privilege | SQL writes through query tools | high | mitigate | `omega_prime/tools/systems.py:294-315` has prefix/EXPLAIN/single-statement checks; `107-138` refuses unconfigured stores. `omega_prime/mcp_server.py:160` supplies no SQL adapter; all configured SQL consumers found in-repo are test fakes. `omega_prime/tests/test_systems.py:73-109` covers direct/multi-statement write refusal and unconfigured behavior; `omega_prime/tests/test_store_lock.py:1-12,96-101` records/asserts the default-None seam. This is NOT a claim that lexical checks enforce arbitrary PostgreSQL read-only semantics; see limits. | closed for shipped consumer, L1 |
| T-46-08 | Information disclosure / Elevation of privilege | Fetch destination SSRF | high | mitigate | `omega_prime/tools/webpack.py:71-95` accepts nonliteral hosts without address validation; `98-106,224-229` passes them to real urllib resolution/connection. `omega_prime/mcp_server.py:161` leaves allowed_hosts unset. `omega_prime/tests/test_web.py:144-166` covers canonical literal refusals only. See SEC-46-SSRF-DESTINATION. | open — blocking |
| T-46-09 | Tampering | Screenshot filename escape | high | mitigate | `omega_prime/tools/webpack.py:48-55,311-322` and `omega_prime/tools/mobile.py:63-70,568-578` reject absolute/traversal/separator names before constructing screenshot targets. `omega_prime/tests/test_web.py:183-209` and `omega_prime/tests/test_mobile.py:272-289` exercise valid and invalid names. No general filesystem/symlink guarantee inferred. | closed, L1 |
| T-46-10 | Elevation of privilege | Production ult_session_mark approval | high | mitigate | `omega_prime/tools/ultrathink.py:31-39,167-174` flags the real mark tool; `omega_prime/tools/registry.py:90-97,167-175` checks policy/approval before handler. `omega_prime/tests/test_ultrathink.py:97-143` covers unapproved mark refusal and approved argument validation; Phase 52 adds production-removal sensitivity. | closed, L1 |
| T-46-11 | Tampering | Stale plan selection | medium | mitigate | `omega_prime/routines/ultrathink_turn.py:49-87` rejects plans older than max_age_hours. `omega_prime/tests/test_ultrathink.py:146-182` checks fresh, malformed/missing, stale, and explicit-age override behavior. | closed, L1 |
| T-46-12 | Information disclosure / Elevation of privilege | Browser rendering bypasses initial URL guard | high | mitigate | `omega_prime/tools/webpack.py:287-304` performs a guarded probe then unrestricted browser navigation; `omega_prime/tools/playwright_browser.py:37-56` creates a page and calls goto with no request interception. `omega_prime/tests/test_web.py:63-71,183-209` uses a non-network fake page, not redirect/subresource refusal coverage. See SEC-46-SSRF-BROWSER. | open — blocking |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 12 | 10 | 2 | V9SecurityGate (read-only specialist); parent artifact integration |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [ ] `threats_open: 0` confirmed.
- [ ] `status: verified` set.

**Approval:** BLOCKED — user disposition required for T-46-08/T-46-12.

## Blocking implementation gaps

### T-46-08: The fetch guard validates host spelling, not the resolved destination

T-46-08 is OPEN (high, blocking). web_preview_check and the rendered-review connectivity probe accept model-controlled URLs without approval. Nonliteral hosts and noncanonical addresses become address=None in _check_url, bypassing address-class checks; the shipped context has no allowed_hosts restriction. Real urllib then resolves/connects without checking the destination. [INFERENCE, not exercised] Private/link-local DNS answers or alternate loopback spellings can reach internal services. Tool-name policy does not enforce the seat's network host list on this separate client.

**Required mitigation:** Validate all resolved A/AAAA destinations, reject non-public addresses and ambiguous numeric forms, and constrain the actual connected peer to a validated destination to prevent rebinding. Enforce configured network policy at the real fetch boundary; preserve no-redirect behavior. Add hermetic resolver/connection refusal tests. Keep this high threat blocking until mitigation is verified or an authorized decision is documented by the parent.

### T-46-12: Rendered review bypasses the fetch guard for browser requests

T-46-12 is OPEN (high, blocking), a separate refinement of Phase 46's SSRF register. web_review_page validates only its initial connectivity probe, then uses an unrestricted Chromium page. No browser request policy covers frames, subresources, redirects or script/meta-refresh navigation. [INFERENCE, not exercised] A public attacker page can pass the probe with HTTP 200 and cause Chromium to request a private/loopback destination, with page metadata and screenshot subsequently captured. urllib's NoRedirects does not apply to this second network path.

**Required mitigation:** Enforce SSRF destination/network policy for every browser request, including redirects, frames, subresources, and script navigation, and constrain actual peer addresses; alternatively require enforced egress sandboxing for this consumer. Add hermetic browser-routing refusal tests independently of the initial connectivity probe. The auditor cannot accept or close this high residual.

User disposition pending. No attack or live-network probe was executed; exploitability is an unexercised inference from the observed control placement. No high risk is accepted by this report.
