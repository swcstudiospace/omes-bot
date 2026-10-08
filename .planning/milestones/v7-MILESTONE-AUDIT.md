---
milestone: v7
audited: 2026-10-03T19:00:00Z
status: passed
scores:
  requirements: 10/10
  phases: 5/5
  integration: 5/5
  flows: 2/2
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - Live Hindsight retain/recall unproven (no API key in this environment; shapes verified against OpenAPI v0.9.1 + fakes)
  - Local substrate-mcp degraded (no ledger/index): emit/search live paths return stored:false/[]; fail-open proven live
  - docs_search returns the raw retrieval payload; chunk extraction deferred until a live dataset answers
  - graph_handoff, lease-steal, and drift scan stay upstream Phase 2 work
---

# Milestone v7 Audit: Substrate surface

## Requirements (10/10)

| Requirement | Phase | Verified by |
|-------------|-------|-------------|
| SUB-01..02 | 39 | 39-VERIFICATION.md |
| HIN-01..02 | 40 | 40-VERIFICATION.md |
| SUB-03, RAG-01 | 41 | 41-VERIFICATION.md |
| GRP-01, LOCK-01 | 42 | 42-VERIFICATION.md |
| PRB-01, SHP-01 | 43 | 43-VERIFICATION.md |

No orphans: every traceability-table requirement is claimed Done in
its phase's VERIFICATION.md. `audit-open` reports zero open items.

## Phases (5/5)

All phases `complete`, all canonical verifications `passed`.

## Integration (5/5)

- Registry/roster/policy/composition agree: 294 pytest passed
  (109 roster tools incl. 5 substrate tools; `default_registry` serves
  108 over MCP with `delegate_task` excluded).
- Deterministic evals: 23/23 passed (incl. 2 substrate machinery cases).
- Prompt assembly: `assemble-prompts.sh --check` exit 0; template
  sections stay empty per contract.
- Store lock: import + endpoint guards green; the `systems.py` injected
  seams asserted `None` by default.
- No new dependencies; no network in tests; live calls confined to the
  manual probes plus one audit E2E snippet (below).

## Flows (2/2)

- Surface turn (live, degraded host): brief fetched (93 chars,
  anonymous) → turn emits return `stored: false` with the 503 reason
  instead of raising → search degrades to `[]`. Fail-open proven
  against the real local substrate-mcp, not just fakes.
- Probe + setup flow: `omega_prime.substrate.probes` reports per-probe
  ok/FAIL with zero secret values; `setup_check` gains the `substrate`
  row (skip unwired, fail on malformed URLs, names-only detail).

## Deferred (accepted)

- Signed handoff packets, lease steal/drift, A2A teachables, OTLP —
  all upstream-phase work, recorded in REQUIREMENTS.md Future.
- Live Hindsight write/read round trip — needs `HINDSIGHT_API_KEY`;
  run the probes + a manual retain/recall once the key exists.
