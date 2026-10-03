# Requirements: v2 Enterprise hardening

Milestone-scoped. v1 requirements are archived in `milestones/v1-REQUIREMENTS.md`.

## Policy engine

- [ ] **POL-01**: A seat policy file declares allowed tools, path roots, and network egress.
- [ ] **POL-02**: The registry refuses a tool the policy does not allow, before execution, and records the refusal.
- [ ] **POL-03**: The policy advisor diffs a proposed policy change and flags expansions for review.
- [ ] **POL-04**: Every tool dispatch appends one audit record to a persisted log.

## Credential broker

- [ ] **CRED-01**: API keys live in the broker, never in transcripts or tool arguments.
- [ ] **CRED-02**: The broker injects a credential only for a request to an approved endpoint.
- [ ] **CRED-03**: Secret-shaped strings are redacted in events, audit records, and rendered output.

## Durable runs

- [ ] **DUR-01**: Every turn is journaled; a crashed turn resumes from the journal.
- [ ] **DUR-02**: Cron jobs record bounded execution history; a completed execution is not re-run for its tick.
- [ ] **DUR-03**: A multi-step workflow checkpoints between steps and resumes from the last checkpoint.

## Transports and traces

- [ ] **NET-01**: A stdlib HTTP transport with retries and timeouts drives provider calls.
- [ ] **OBS-01**: Turns export a structured trace of model calls, tool calls, and policy verdicts.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POL-01 | Phase 13 | Pending |
| POL-02 | Phase 13 | Pending |
| POL-03 | Phase 13 | Pending |
| POL-04 | Phase 13 | Pending |
| CRED-01 | Phase 14 | Pending |
| CRED-02 | Phase 14 | Pending |
| CRED-03 | Phase 14 | Pending |
| DUR-01 | Phase 15 | Pending |
| DUR-02 | Phase 15 | Pending |
| DUR-03 | Phase 15 | Pending |
| NET-01 | Phase 16 | Pending |
| OBS-01 | Phase 16 | Pending |

**Coverage:**

- v2 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v2 milestone)*
