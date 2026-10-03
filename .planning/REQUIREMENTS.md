# Requirements: v3 Grok Bot

Milestone-scoped. v2 requirements are archived in `milestones/v2-REQUIREMENTS.md`.

## X connector

- [ ] **X-01**: Read mentions and posts through the X connector with a fake transport.
- [ ] **X-02**: Post and thread publish through the connector; publishing requires approval.
- [ ] **X-03**: Media upload stages bytes and returns a media id.

## Engagement sweep

- [ ] **ENG-01**: A sweep turns mentions into queued reply drafts.
- [ ] **ENG-02**: The sweep runs as a checkpointed workflow and resumes after interruption.

## Nightly learning

- [ ] **LRN-01**: A nightly pass reviews transcripts and creates earned skills.
- [ ] **LRN-02**: Unearned turns write nothing.

## Eval harness

- [ ] **EV-01**: Golden evals assert persona behavior deterministically.
- [ ] **EV-02**: Red-team evals assert policy refusals.
- [ ] **EV-03**: CI runs the suite plus the evals.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| X-01 | Phase 17 | Pending |
| X-02 | Phase 17 | Pending |
| X-03 | Phase 17 | Pending |
| ENG-01 | Phase 18 | Pending |
| ENG-02 | Phase 18 | Pending |
| LRN-01 | Phase 19 | Pending |
| LRN-02 | Phase 19 | Pending |
| EV-01 | Phase 20 | Pending |
| EV-02 | Phase 20 | Pending |
| EV-03 | Phase 20 | Pending |

**Coverage:**

- v3 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v3 milestone)*
