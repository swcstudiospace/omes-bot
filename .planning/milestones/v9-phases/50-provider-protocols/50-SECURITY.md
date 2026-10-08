---
phase: "50"
slug: "provider-protocols"
status: verified
threats_open: 0
threats_total: 4
threats_closed: 4
asvs_level: 1
block_on: high
register_authored_at_plan_time: false
created: "2026-10-07"
---

# Phase 50 — Security

## Trust Boundaries

transcript → external API routing/storage; response/SSE deltas → assistant/tool calls; partial transport → retry behavior.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-50-01 | Information disclosure | Responses retention/reasoning disclosure | high | mitigate | `omes/providers/openai.py:59-74` sends store:false; `240-285` extracts supported message/function-call output, not reasoning items. `omes/tests/test_providers.py:462-541` checks request storage flag and reasoning exclusion. This verifies client requests, not vendor retention implementation. | closed, L1 |
| T-50-02 | Elevation of privilege | Wrong provider/host or unsafe fallback | high | mitigate | `omes/providers/openai.py:29-37,97-126` selects modes and keeps fallback on the same base URL/key; `omes/providers/base.py:145-182` tries one fallback only; `omes/credentials/broker.py:29-47` and `omes/providers/http.py:100-105` enforce configured host authorization. `omes/tests/test_providers.py:161-180,579-628` covers routing/fallback/error cases; `omes/tests/test_credentials.py:62-81` covers credential host refusal before calls. | closed, L1 |
| T-50-03 | Tampering / Elevation of privilege | Streamed calls create a new execution/approval path | high | mitigate | `omes/providers/openai.py:137-201`, `anthropic.py:91-161`, `gemini.py:104-153`, `ollama.py:66-115` normalize calls into ordinary assistant rows; `omes/providers/base.py:215-232`, `omes/agent/conversation_loop.py:208-232`, and `omes/agent/turn_tool_round.py:38-51,96-110` retain the ordinary tool consumer, not execution of output text. Registry controls remain `omes/tools/registry.py:90-97`. `omes/tests/test_providers.py:642-780` checks accumulated calls/usage; `omes/tests/test_transports.py:363-382` checks streamed loop consumption. | closed, L1 |
| T-50-04 | Tampering / Repudiation | Retrying after partial stream replays output/actions | high | mitigate | `omes/providers/http.py:181-223` converts setup/status failures to retryable errors but leaves body-read failures outside that retryable conversion and closes the connection; `omes/providers/base.py:225-228` surfaces stream failures before returning an assistant row. `omes/tests/test_transports.py:330-360` tests pre-body status retry/nonretry behavior. No dedicated after-first-byte runtime test was observed; closure here is source-level L1. | closed, L1 |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 4 | 4 | 0 | V9SecurityGate (read-only specialist); parent artifact integration |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-07, scoped ASVS L1.
