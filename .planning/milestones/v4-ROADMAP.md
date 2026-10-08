# Roadmap: Omega Prime v4

## Overview

v3 shipped the Grok Bot (see `milestones/v3-ROADMAP.md`). v4 wires in third-party libraries as real pip dependencies: a live X transport, a standards-based MCP session client, deeper red-team evals, a real scheduler backend, and two new messaging connectors. Numbering continues. A phase is done when its parity checks pass.

## Phases

- [x] **Phase 21: Tweepy X transport** - XClient behind `tweepy.Client`, brokered token, fakes still default.
- [x] **Phase 22: MCP SDK layer** - Session-based MCP client on the official SDK beside one-shot `mcp_call`.
- [x] **Phase 23: Red-team depth** - Omega Prime as a PyRIT target with a keyless structural battery in CI.
- [x] **Phase 24: Scheduler backend** - APScheduler drives JobStore jobs; JSON store stays authoritative.
- [x] **Phase 25: Messaging connectors** - Telegram (aiogram) and Discord (discord.py) in the Phase 17 shape.

## Phase Details

### Phase 21: Tweepy X transport
**Goal**: The connector speaks live X through tweepy while tests stay offline.
**Depends on**: v3 complete
**Requirements**: XTP-01, XTP-02
**Success Criteria** (what must be TRUE):
  1. Each XClient operation maps to the matching `tweepy.Client` call with the brokered token.
  2. The suite runs with no X credentials and makes no live calls.
**Plans**: 1 plan

Plans:
- [x] 21-01: Tweepy transport adapter and dependency

### Phase 22: MCP SDK layer
**Goal**: Real MCP servers that require the initialize handshake become callable.
**Depends on**: Phase 21
**Requirements**: MCP-01, MCP-02
**Success Criteria** (what must be TRUE):
  1. A session client completes initialize plus tools/call against a scripted stdio server via the SDK.
  2. String commands are refused, missing cwd is refused, timeouts kill the child.
**Plans**: 1 plan

Plans:
- [x] 22-01: SDK session client and dependency

### Phase 23: Red-team depth
**Goal**: Scripted adversarial batteries attack the real agent loop and assert refusals.
**Depends on**: Phase 22
**Requirements**: RT-01, RT-02
**Success Criteria** (what must be TRUE):
  1. A PyRIT target wraps `run_conversation` and the registry dispatch path.
  2. A keyless battery of adversarial prompts runs in CI and asserts structural refusals.
**Plans**: 1 plan

Plans:
- [x] 23-01: PyRIT target adapter and battery

### Phase 24: Scheduler backend
**Goal**: JobStore jobs run on a real scheduler (v3 deferred item).
**Depends on**: Phase 23
**Requirements**: SCH-01, SCH-02
**Success Criteria** (what must be TRUE):
  1. Date and interval jobs fire through APScheduler and record results in the JSON store.
  2. Claim, bounded history, and resume-after-restart semantics hold.
**Plans**: 1 plan

Plans:
- [x] 24-01: APScheduler backend and dependency

### Phase 25: Messaging connectors
**Goal**: Telegram and Discord join X as approval-gated connector families.
**Depends on**: Phase 24
**Requirements**: MSG-01, MSG-02, MSG-03
**Success Criteria** (what must be TRUE):
  1. Telegram reads and approval-gated sends work through aiogram with a brokered token.
  2. Discord reads and approval-gated sends work through discord.py with a brokered token.
  3. Both families register tools, roster entries, and run offline in tests.
**Plans**: 1 plan

Plans:
- [x] 25-01: Telegram and Discord connectors and dependencies

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 21. Tweepy X transport | 1/1 | Complete | 2026-10-03 |
| 22. MCP SDK layer | 1/1 | Complete | 2026-10-03 |
| 23. Red-team depth | 1/1 | Complete | 2026-10-03 |
| 24. Scheduler backend | 1/1 | Complete | 2026-10-03 |
| 25. Messaging connectors | 1/1 | Complete | 2026-10-03 |
