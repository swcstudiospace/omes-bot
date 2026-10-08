---
phase: "49"
slug: "provider-resilience"
status: verified
threats_open: 0
threats_total: 3
threats_closed: 3
asvs_level: 1
block_on: high
register_authored_at_plan_time: false
created: "2026-10-07"
---

# Phase 49 — Security

## Trust Boundaries

provider HTTP statuses/headers → retries; provider counters → model spans.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-49-01 | Denial of service | Unbounded transient retries/Retry-After | medium | mitigate | `omes/providers/http.py:106-118,146-153,291-313` bounds attempts/delay, retries 408/429, and caps Retry-After at 60 seconds. `omes/tests/test_transports.py:163-219` covers success, recorded delay/cap, exhaustion, and no sleep with zero backoff. | closed, L1 |
| T-49-02 | Tampering | Malformed usage counters | medium | mitigate | `omes/providers/base.py:100-118` accepts nonnegative integers excluding bool; per-adapter usage mappings are present. `omes/tests/test_providers.py:388-419` checks all five providers and junk/absent/negative/bool values. Counters are metadata, not authorization. | closed, L1 |
| T-49-03 | Repudiation | Missing/stale per-turn attribution | low | mitigate | `omes/providers/base.py:200-213,215-232` stores current parsed usage; `omes/agent/conversation_loop.py:208-210,346-367` records spans after successful completion. `omes/tests/test_providers.py:422-453` and `omes/tests/test_transports.py:283-327` check present and absent usage. Failed completions do not reach span emission. | closed, L1 |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 3 | 3 | 0 | V9SecurityGate (read-only specialist); parent artifact integration |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-07, scoped ASVS L1.
