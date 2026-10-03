# Milestone v3 archive — ROADMAP (completed 2026-10-03)

# Roadmap: Omes Bot v3

## Overview

v2 hardened the agent (see `milestones/v2-ROADMAP.md`). v3 turns it into a Grok Bot: an X connector tool family, an engagement sweep routine, nightly learning wired through the curator and autolearn, and an eval harness with CI. Numbering continues. A phase is done when its parity checks pass.

## Phases

**Phase Numbering:**

- Integer phases (17, 18, 19, 20): Planned v3 milestone work
- Decimal phases (17.1, 17.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 17: X connector** - Mentions, posts, threads, and media upload behind the broker.
- [x] **Phase 18: Engagement sweep** - Mentions in, queued reply drafts out, checkpointed.
- [x] **Phase 19: Nightly learning** - Transcripts reviewed, earned skills created.
- [x] **Phase 20: Eval harness** - Golden persona evals, red-team policy evals, CI.

## Phase Details

### Phase 17: X connector
**Goal**: The agent reads and publishes on X through approval-gated registry tools, with credentials brokered per endpoint.
**Depends on**: v2 complete
**Requirements**: X-01, X-02, X-03
**Success Criteria** (what must be TRUE):
  1. Mentions and single posts read through the connector with a fake transport.
  2. Post and thread publish through the connector; both require approval, and unapproved publishing is refused.
  3. Media bytes upload and return a media id that a post can attach.
**Plans**: 1 plan

Plans:
- [x] 17-01: X client, registry tools, and approval-gated publishing

### Phase 18: Engagement sweep
**Goal**: A scheduled sweep converts fresh mentions into queued reply drafts without publishing.
**Depends on**: Phase 17
**Requirements**: ENG-01, ENG-02
**Success Criteria** (what must be TRUE):
  1. A sweep over fixture mentions produces one draft per mention with reply targets and text.
  2. The sweep checkpoints per mention and resumes after interruption without duplicating drafts.
**Plans**: 1 plan

Plans:
- [x] 18-01: Sweep routine with drafts and checkpoints

### Phase 19: Nightly learning
**Goal**: The curator's nightly pass turns earned turns into skills and ignores the rest.
**Depends on**: Phase 18
**Requirements**: LRN-01, LRN-02
**Success Criteria** (what must be TRUE):
  1. A nightly pass over fixture transcripts creates skills for earned turns through the curator.
  2. Unearned turns write no skills.
**Plans**: 1 plan

Plans:
- [x] 19-01: Nightly curator pass over transcripts

### Phase 20: Eval harness
**Goal**: Deterministic evals guard the persona and the policy, and CI runs everything.
**Depends on**: Phase 19
**Requirements**: EV-01, EV-02, EV-03
**Success Criteria** (what must be TRUE):
  1. Golden evals replay scripted turns and assert persona behavior from a cases file.
  2. Red-team evals assert refusals for prompt-injection, exfiltration, and policy-escape attempts.
  3. A CI workflow runs the suite and the evals.
**Plans**: 1 plan

Plans:
- [x] 20-01: Eval cases, runner, and CI workflow

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. X connector | 1/1 | Complete | 2026-10-03 |
| 18. Engagement sweep | 1/1 | Complete | 2026-10-03 |
| 19. Nightly learning | 1/1 | Complete | 2026-10-03 |
| 20. Eval harness | 1/1 | Complete | 2026-10-03 |
