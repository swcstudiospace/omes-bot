---
phase: "47"
slug: "lint-types"
status: verified
threats_open: 0
threats_total: 2
threats_closed: 2
asvs_level: 1
block_on: high
register_authored_at_plan_time: false
created: "2026-10-07"
---

# Phase 47 — Security

## Trust Boundaries

source/config → enforced CI gates; registry outputs → MCP wire schema/error semantics.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-47-01 | Tampering | Missing/bypassed CI lint/type checks | medium | mitigate | `pyproject.toml:33-36,57-72` declares pinned gates; `.github/workflows/ci.yml:26-56` installs dev dependencies and invokes checks without failure suppression. Final parent Ruff lint/format and mypy commands exit 0. Obsolete source/configuration-copy tests were removed; no CI execution or branch-protection claim. | closed, L1 |
| T-47-02 | Tampering / Repudiation | MCP canonicalization loses schema/refusal flags | high | mitigate | `omes/mcp_server.py:190-203,220-241` uses canonical SDK fields and decoded error semantics. `omes/tests/test_mcp_server.py:40-82,96-115` exercises actual SDK schema and unknown/approval/roster refusals, green in the final 344-test suite. Source-spelling proxy removed. | closed, L1 |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 2 | 2 | 0 | V9SecurityGate (read-only specialist); parent artifact integration |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-07, scoped ASVS L1.
