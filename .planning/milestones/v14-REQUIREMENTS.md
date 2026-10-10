# Requirements: Omega Prime v14 Boundary alignment

**Defined:** 2026-10-10
**Archived:** 2026-10-10
**Outcome:** All 10 requirements validated. BND-05 and BND-06 counts were updated from 110/147 to 117/154 because phase 73 added seven always-on tools, as the milestone notes required. No requirement was dropped. Audit passed (`.planning/v14-MILESTONE-AUDIT.md`).

**Core Value:** The agent loop and harness core are the center. The Grok Bot boundary makes every ported logic usable through it, and nothing in the core imports the boundary.

## Phase 71 — Core/boundary inversion repair

- [x] **BND-01**: No module under `omega_prime/agent/` or `omega_prime/tools/` imports `omega_prime.grokbot`. The slash-command engine (parser, catalog, executor, workflows, seed) lives in a core package; `agent/runtime.py` and `tools/omega_command.py` import it from there. `grep -rn "omega_prime\.grokbot" omega_prime/agent omega_prime/tools` returns nothing.
- [x] **BND-02**: `mcp_server.py` no longer imports the private `grokbot._io`. The helper it needs is public and owned by the layer that should own it.
- [x] **BND-03**: Nested dispatch from `omega_command` (command tool passthrough and workflow steps) re-enters the boundary's roster + interceptor chain for the calling principal when the command arrives through the host. In-process turns (agent intercept, cron) keep registry-gate semantics. Proven by tests: a recording interceptor observes inner calls; an inner call for an over-quota principal is limited; an inner call to a tool not on the caller's roster is denied.
- [x] **BND-04**: One roster parser. A single function owns reading tool names from `contracts/tool-rosters/omega-prime.yaml`; `mcp_server` and every test use it, not ad-hoc copies.

## Phase 72 — Family reachability

- [x] **BND-05**: `prime.rlm.enabled` and `prime.messaging.enabled` actually serve their families through the default host. Flag on → the seven `rlm_*` names and `agent_message_send`/`agent_observe` register and answer (explicit `not_configured` results without credentials, never an exception). Flag off (default) → absent. After phase 73 the default served count is 117 (was 110 before the seven plane tools).
- [x] **BND-06**: With all seven Prime flags on, the host serves exactly the roster names. After phase 73 that set is 154 (was 147 before the seven plane tools). `setup_check` proves roster == served with all flags on. Docs state the real numbers and how to turn families on.

## Phase 73 — Plane surfaces

- [x] **BND-07**: The cron plane is usable through the boundary: schedule list/create/remove tools over the shared JobStore; mutating ops are approval-gated per seat-policy convention; the scheduler and DeskDriver behave unchanged.
- [x] **BND-08**: The learning plane is usable: autolearn and advisor surfaces are registered and served; GoalStore reachability is verified through the goals family and stated in the phase summary with tool names.
- [x] **BND-09**: The durable plane is wired: the TurnJournal is attached to the production Agent constructions (cron job runs, delegate children) and a served read tool exposes journal/status.

## Phase 74 — Closeout

- [x] **BND-10**: Milestone audit with per-requirement evidence; v14 archived; full gates green on the final tree.

## Traceability

| ID | Phase | Outcome |
|---|---|---|
| BND-01 | 71 | validated |
| BND-02 | 71 | validated |
| BND-03 | 71 | validated |
| BND-04 | 71 | validated |
| BND-05 | 72 | validated; default count updated to 117 by phase 73 |
| BND-06 | 72 | validated; all-flags count updated to 154 by phase 73 |
| BND-07 | 73 | validated |
| BND-08 | 73 | validated |
| BND-09 | 73 | validated |
| BND-10 | 74 | validated |

## Notes

- Phase 73 added `cron_jobs_list`, `cron_job_create`, `cron_job_remove`, `autolearn_turn`, `advisor_note`, `advisor_render`, and `durable_status`. Roster, policy, catalog, composition tests, and docs moved together.
- Default-off Prime families stay default-off. v14 makes flags functional, not default-on.
