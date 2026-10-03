# Milestone v2 archive — REQUIREMENTS (all Done, 2026-10-03)

# Requirements: v2 Enterprise hardening

Milestone-scoped. v1 requirements are archived in `milestones/v1-REQUIREMENTS.md`.

## Policy engine

- [x] **POL-01**: A seat policy file declares allowed tools, path roots, and network egress.
- [x] **POL-02**: The registry refuses a tool the policy does not allow, before execution, and records the refusal.
- [x] **POL-03**: The policy advisor diffs a proposed policy change and flags expansions for review.
- [x] **POL-04**: Every tool dispatch appends one audit record to a persisted log.

## Credential broker

- [x] **CRED-01**: API keys live in the broker, never in transcripts or tool arguments.
- [x] **CRED-02**: The broker injects a credential only for a request to an approved endpoint.
- [x] **CRED-03**: Secret-shaped strings are redacted in events, audit records, and rendered output.

## Durable runs

- [x] **DUR-01**: Every turn is journaled; a crashed turn resumes from the journal.
- [x] **DUR-02**: Cron jobs record bounded execution history; a completed execution is not re-run for its tick.
- [x] **DUR-03**: A multi-step workflow checkpoints between steps and resumes from the last checkpoint.

## Transports and traces

- [x] **NET-01**: A stdlib HTTP transport with retries and timeouts drives provider calls.
- [x] **OBS-01**: Turns export a structured trace of model calls, tool calls, and policy verdicts.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POL-01 | Phase 13 | Done |
| POL-02 | Phase 13 | Done |
| POL-03 | Phase 13 | Done |
| POL-04 | Phase 13 | Done |
| CRED-01 | Phase 14 | Done |
| CRED-02 | Phase 14 | Done |
| CRED-03 | Phase 14 | Done |
| DUR-01 | Phase 15 | Done |
| DUR-02 | Phase 15 | Done |
| DUR-03 | Phase 15 | Done |
| NET-01 | Phase 16 | Done |
| OBS-01 | Phase 16 | Done |

**Coverage:**

- v2 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v2 milestone)*
*Last updated: 2026-10-03 after milestone audit (all 12 requirements Done)*
