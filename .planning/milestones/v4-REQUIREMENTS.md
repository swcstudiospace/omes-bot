# Requirements: v4 Third-party integrations

Milestone-scoped. v3 requirements are archived in `milestones/v3-REQUIREMENTS.md`.

## Tweepy X transport

- [x] **XTP-01**: XClient runs behind a tweepy transport mapping mentions, reads, posts, threads, and media upload to `tweepy.Client` calls with brokered credentials.
- [x] **XTP-02**: The fake transport stays the default in tests; the suite makes no live X calls.

## MCP SDK layer

- [x] **MCP-01**: A session-based MCP client uses the official MCP Python SDK (initialize handshake plus tools/call) alongside the one-shot `mcp_call`.
- [x] **MCP-02**: The session client keeps the one-shot safety contract: argv list only, cwd must exist, timeout kills the child.

## Red-team depth

- [x] **RT-01**: The Omes agent is exposed as a PyRIT target so scripted adversarial batteries run against `run_conversation` and the registry.
- [x] **RT-02**: The adversarial battery runs in CI with no model keys and asserts refusals structurally.

## Scheduler backend

- [x] **SCH-01**: An APScheduler backend drives JobStore jobs (date and interval triggers) with the JSON store as the source of truth.
- [x] **SCH-02**: Existing tick semantics hold: claimed jobs are not re-run, history stays bounded, restarts resume.

## Messaging connectors

- [x] **MSG-01**: A Telegram connector (aiogram) reads updates and sends messages; sending requires approval; the token is brokered.
- [x] **MSG-02**: A Discord connector (discord.py) reads messages and sends messages; sending requires approval; the token is brokered.
- [x] **MSG-03**: Both connectors follow the Phase 17 pattern: client plus `register_*_tools`, roster entries, fake async peers in tests.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| XTP-01 | Phase 21 | Done |
| XTP-02 | Phase 21 | Done |
| MCP-01 | Phase 22 | Done |
| MCP-02 | Phase 22 | Done |
| RT-01 | Phase 23 | Done |
| RT-02 | Phase 23 | Done |
| SCH-01 | Phase 24 | Done |
| SCH-02 | Phase 24 | Done |
| MSG-01 | Phase 25 | Done |
| MSG-02 | Phase 25 | Done |
| MSG-03 | Phase 25 | Done |

**Coverage:**

- v4 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v4 milestone)*
