---
phase: "52"
slug: "answers-evals-docs"
status: verified
threats_open: 0
threats_total: 5
threats_closed: 5
asvs_level: 1
block_on: high
register_authored_at_plan_time: false
created: "2026-10-07"
---

# Phase 52 — Security

## Trust Boundaries

RAGflow/substrate envelope → exported excerpt/metadata/errors; exported result → registry/MCP/next model request; eval setup → production approval authority.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-52-01 | Information disclosure | Raw retrieval escapes excerpt control (CR-01) | high | mitigate | `omes/tools/substrate_tools.py:110-113,135-195` emits only explicit shaped chunks, no raw branch. `omes/tests/test_substrate_session.py:200-267` checks whole serialized output/raw absence/content sentinel; `omes/tests/test_mcp_server.py:165-203` checks actual MCP text. Supplied consumer smoke (`local://omes-v9-gate-evidence.md:15`) reaches decoder, registry, MCP, loop and next model request. | closed |
| T-52-02 | Information disclosure | Metadata/error bypass (CR-02) | high | mitigate | `omes/tools/substrate_tools.py:89-108,145-195` types/redacts labels/IDs, allows only finite numeric scores and bounded nonnegative-integer citation positions, and redacts/bounds all upstream error branches. `omes/credentials/redact.py:45-55` supplies recursive final-value redaction. `omes/tests/test_substrate_session.py:235-339` checks whole-result metadata/types/zero/error branches; supplied smoke verifies safe IDs/positions, NaN→null and redacted error. | closed |
| T-52-03 | Tampering / Repudiation | Denial/malformed appears as empty (WR-01) | medium | mitigate | `omes/tools/substrate_tools.py:92-132` separates failed/nonzero/malformed responses from genuine empty lists; `omes/mcp_server.py:237-241` flags error-key payloads. `omes/tests/test_substrate_session.py:341-387` covers 11 malformed envelopes plus genuine-empty/top-level controls; `omes/tests/test_mcp_server.py:205-215` checks malformed MCP status. Supplied smoke verifies malformed/empty/error distinction. | closed |
| T-52-04 | Elevation of privilege | Stub eval approval diverges from production (WR-02) | high | mitigate | `omes/evals/runner.py:119-139,147-187` uses real ultrathink registration and records injected runner invocations instead of self-declared family approval. `omes/tools/ultrathink.py:31-39,167-174` is authoritative. `omes/tests/test_evals.py:66-85` removes production mark approval, requires red-team failure, then verifies restoration; `omes/evals/cases/golden.json:151-162` and `redteam.json:170-194` cover approved/refused mark and empty allowlist denial. `omes/policy/policy.py:26-28,52-56` treats explicit [] as deny-all. Supplied eval CLI: 26 passed. | closed |
| T-52-05 | Denial of service | Unbounded exported field/citation payload | medium | mitigate | `omes/tools/substrate_tools.py:18-20,155-161,172-195` applies excerpt/label/error slice caps and limits positions to 32 entries of 1–5 integer coordinates, dropping arbitrary vendor fields. `omes/tests/test_substrate_session.py:235-267,306-330` checks long-content/error bounds; supplied smoke checks beyond-cap exclusion and safe positions. This is not a claim of a global incoming HTTP-body/chunk-count limit. | closed, field-level L1 |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 5 | 5 | 0 | V9SecurityGate (read-only specialist); parent artifact integration |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-07, scoped ASVS L1.
