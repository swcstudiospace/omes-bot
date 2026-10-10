# Phase 73 Context: Plane surfaces

**Requirements:** BND-07, BND-08, BND-09.

Three core planes have no Grok-boundary surface (2026-10-10 map):

- **Cron**: `cron/scheduler.py` runs `jobs.json` jobs and `DeskDriver` ticks
  desk passes, but no served tool creates/lists/removes schedules. The plane
  exists and runs; it is only administrable by editing the store file.
- **Learning**: `learning/harness.py` backs the gated `harness_*` tools;
  `learning/autolearn.py`, `learning/advisor.py`, and the GoalStore path in
  `learning/goals.py` have no serving import outside `learning/`.
- **Durable**: `durable/journal.py` (TurnJournal) and `durable/workflows.py`
  are a conversation_loop option and tests only — no production construction
  passes a journal, and no tool observes it.

Naming and gating follow family conventions: JSON dict results,
`not_configured`-style explicit results over exceptions, write-kind tools
approval-gated, roster names listed in served order with the family grouped.

Phase 73 adds tool names, so the roster grows past 147 and the default served
count grows past 110. Roster YAML, policy allow list, `tooling/catalog.py`
FAMILIES, composition tests, and every doc count must move together in the
integration step — the v13 lesson (109→110 misses) applies.
