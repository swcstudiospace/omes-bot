# Phase 73 Plan: Plane surfaces

**Requirements:** BND-07, BND-08, BND-09.

## Wave 1 (parallel; disjoint new modules; no registry edits)

- **Task cron**: `omega_prime/tools/cron_admin.py` — list/create/remove
  schedules over the shared JobStore (`root/cron/jobs.json` semantics from
  `cron/scheduler.py`). Reads served; writes approval-gated by kind
  (`_WRITE_TOOLS` frozenset convention). Unit tests with a temp store.
- **Task learning**: read `learning/autolearn.py`, `learning/advisor.py`,
  `learning/goals.py`. Register autolearn and advisor surfaces in a new
  `omega_prime/tools/learning_surface.py`; verify GoalStore reachability via
  the existing gated goals family and record the tool names. Unit tests.
- **Task durable**: wire the TurnJournal into the production Agent
  constructions (`cron/scheduler.py run_due_jobs`, `agent/delegate.py`
  children) behind a default-on or config-flagged path that cannot break
  existing turns (journal failure must degrade loudly, not raise); add a
  served read tool `durable_status` in `omega_prime/tools/durable_surface.py`
  exposing journal/checkpoint state. Unit tests.

Each task exports `register_*_tools(registry, ...) -> list[str]` and a
`*_TOOL_NAMES` tuple; no roster/policy/catalog edits (integration owns them).

## Wave 2 (after all three)

- **Task integrate**: register the three families in `default_registry` in
  roster-grouped positions; add names to `contracts/tool-rosters/omega-prime.yaml`
  and the policy allow list; add families to `tooling/catalog.py` FAMILIES;
  update composition tests (`OMEGA_COMMAND_TOOL_NAMES`-style ordering tests);
  regenerate `docs/tool-catalog.md`; update every stale count (grep `110`,
  `147`, `26 skills`) across README/docs/ARCHITECTURE.md.

## Acceptance

- Every new tool answers JSON dicts; missing config ⇒ explicit
  `not_configured` results; writes approval-gated.
- Scheduler + DeskDriver behavior unchanged (existing cron tests green).
- Roster == registry == policy == catalog; composition tests assert the new
  names in the right slots; docs counts match `setup_check` output.

Skip full gates; orchestrator runs them.
