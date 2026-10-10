# Roadmap: Omega Prime

## v14 Boundary alignment — shipped 2026-10-10

**Status:** Complete. 4/4 phases, 10/10 requirements. Audit passed.

The agent loop and harness core are the center. The Grok Bot boundary makes every ported logic usable through it, and nothing in the core imports the boundary.

- [x] **Phase 71: Core/boundary inversion repair** — Slash engine in core, no core→grokbot imports, nested dispatch through boundary gates, one roster parser. (BND-01..04)
- [x] **Phase 72: Family reachability** — `rlm` and `messaging` served behind their flags; all-flags-on host serves the roster set. (BND-05..06)
- [x] **Phase 73: Plane surfaces** — Cron schedule tools, learning surfaces, durable journal wiring; roster/policy/catalog/docs counts updated together. (BND-07..09)
- [x] **Phase 74: Milestone audit + closeout** — Audit, archive, full gates. (BND-10)

### Phase 71: Core/boundary inversion repair

**Goal:** The slash engine is core. Nested host calls re-enter the roster and interceptor chain. One function parses the roster YAML.
**Requirements:** BND-01, BND-02, BND-03, BND-04
**Success criteria:**

  1. `rg` under `agent/` and `tools/` finds no `omega_prime.grokbot` import.
  2. `mcp_server` does not import `grokbot._io`.
  3. A recording interceptor, a rate limit, and a roster omission apply to an inner `omega_command` tool call.
  4. `mcp_server` and the tests use `omega_prime.tooling.roster.roster_names`.

### Phase 72: Family reachability

**Goal:** Turning `rlm` or `messaging` on serves that family. Turning every Prime flag on serves the roster set.
**Requirements:** BND-05, BND-06
**Success criteria:**

  1. Flag off: the nine names are absent.
  2. `rlm` on, no provider: seven `rlm_*` tools answer `not_configured: provider` where a child is required, and never raise.
  3. `messaging` on: `agent_message_send` and `agent_observe` round-trip.
  4. All seven flags: served set equals roster set (154 after phase 73).

### Phase 73: Plane surfaces

**Goal:** Cron, learning, and durable turns are usable through the boundary. Counts move together.
**Requirements:** BND-07, BND-08, BND-09
**Success criteria:**

  1. `cron_jobs_list`, `cron_job_create`, and `cron_job_remove` use the shared `JobStore`. Writes are approval-gated.
  2. `autolearn_turn`, `advisor_note`, and `advisor_render` are served. GoalStore stays on `goal_set`, `goal_pause`, `goal_resume`, `goal_clear`, `goal_status`.
  3. Cron jobs and delegate children journal. `durable_status` reports the cron journal.
  4. Default host serves 117. All flags serve 154.

### Phase 74: Milestone audit + closeout

**Goal:** Every requirement has command evidence, the phase directories are archived, and the final tree is green.
**Requirements:** BND-10
**Success criteria:**

  1. `.planning/v14-MILESTONE-AUDIT.md` status is `passed`.
  2. Phase directories live under `milestones/v14-phases/`.
  3. pytest, mypy, ruff, evals, assemble, catalog, and setup_check pass on the final tree.

## Decisions

- The slash engine is application core. `grokbot/` keeps transport and bot operations.
- Nested dispatch is a context var set by the host call path. In-process callers keep registry dispatch.
- `rlm` and `messaging` stay default-off. The flags now register them on the default host.
- `rlm` reuses the desk parent. It does not grow a second child runner.
- Phase 73's seven tools are always served. They changed the milestone counts from 110/147 to 117/154.
- Prime families stay off by default.

## Known limits

No live Grok account and no live model call. `durable_status` reads the cron journal, not the desk-parent journal. Nyquist and security phase artifacts were not generated. Closeout does not commit or tag.
