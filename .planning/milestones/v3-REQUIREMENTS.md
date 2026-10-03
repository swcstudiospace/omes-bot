# Milestone v3 archive — REQUIREMENTS (all Done, 2026-10-03)

# Requirements: v3 Grok Bot

Milestone-scoped. v2 requirements are archived in `milestones/v2-REQUIREMENTS.md`.

## X connector

- [x] **X-01**: Read mentions and posts through the X connector with a fake transport.
- [x] **X-02**: Post and thread publish through the connector; publishing requires approval.
- [x] **X-03**: Media upload stages bytes and returns a media id.

## Engagement sweep

- [x] **ENG-01**: A sweep turns mentions into queued reply drafts.
- [x] **ENG-02**: The sweep runs as a checkpointed workflow and resumes after interruption.

## Nightly learning

- [x] **LRN-01**: A nightly pass reviews transcripts and creates earned skills.
- [x] **LRN-02**: Unearned turns write nothing.

## Eval harness

- [x] **EV-01**: Golden evals assert persona behavior deterministically.
- [x] **EV-02**: Red-team evals assert policy refusals.
- [x] **EV-03**: CI runs the suite plus the evals.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| X-01 | Phase 17 | Done |
| X-02 | Phase 17 | Done |
| X-03 | Phase 17 | Done |
| ENG-01 | Phase 18 | Done |
| ENG-02 | Phase 18 | Done |
| LRN-01 | Phase 19 | Done |
| LRN-02 | Phase 19 | Done |
| EV-01 | Phase 20 | Done |
| EV-02 | Phase 20 | Done |
| EV-03 | Phase 20 | Done |

**Coverage:**

- v3 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v3 milestone)*
*Last updated: 2026-10-03 after milestone audit (all 10 requirements Done)*
