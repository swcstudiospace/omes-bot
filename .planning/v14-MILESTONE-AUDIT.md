---
milestone: v14
name: Boundary alignment
audited: 2026-10-10
status: passed
scores:
  requirements: 10/10
  phases: 4/4
  integration: 3/3
  flows: 6/6
requirement_disposition: all-wired
active_phase: none
open: []
exceptions: []
nyquist:
  compliant_phases: []
  partial_phases: []
  not_validated_phases: []
  missing_phases: [71, 72, 73, 74]
  overall: missing
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt: []
---

# v14 milestone audit: passed

**Scope.** Put the agent loop and harness at the center. The Grok Bot boundary makes the ported logic usable: slash commands stay in core, nested tool calls re-enter the host gates, `rlm` and `messaging` actually serve when their flags are on, and cron, learning, and durable turns have a boundary surface. Nothing in `agent/` or `tools/` imports the boundary.

**Result.** BND-01..10 satisfied. No exceptions. The requirement text for BND-05 and BND-06 named 110 and 147. Those were the counts before phase 73. Phase 73 added seven always-on tools, which the requirements notes said must update the counts in the same milestone. Final counts: 117 served by default, 154 with all seven Prime flags on, served set equal to the roster set.

Integration was checked in this closeout (no separate checker subagent is available in this runtime). Phase 71 owns the core command package, the public file helper, the single roster parser, and the nested-dispatch scope. Phase 72 registers `rlm` and `messaging` on `default_registry` behind the existing flags. Phase 73 registers cron, learning, and durable tools on that same registry and puts the new names on the roster, the policy, and the catalog.

Nyquist `VALIDATION.md` and security `SECURITY.md` files were not produced for phases 71–74. That is a process gap. It is not an unsatisfied requirement: the behaviors below were exercised by tests and by the final-tree gates.

## Requirement-by-requirement

| Requirement | Status | Evidence |
|---|---|---|
| BND-01 core does not import grokbot | WIRED | `71-VERIFICATION.md`. Slash engine is `omega_prime/commands/`. `rg` under `agent/` and `tools/` finds no `omega_prime.grokbot` import. |
| BND-02 no private `_io` import | WIRED | `71-VERIFICATION.md`. `grokbot/_io.py` moved to `omega_prime/tooling/fs.py`. `mcp_server` uses `read_secret_file`. |
| BND-03 nested dispatch re-enters host gates | WIRED | `71-VERIFICATION.md`. Recording interceptor, rate limit, and roster omission cover the inner call. In-process dispatch stays on the registry. |
| BND-04 one roster parser | WIRED | `71-VERIFICATION.md`. `omega_prime.tooling.roster.roster_names`. |
| BND-05 rlm and messaging serve behind flags | WIRED | `72-VERIFICATION.md`. Flag off: absent. Flag on: seven `rlm_*` names and `agent_message_send` / `agent_observe`. No provider: `not_configured: provider`, not an exception. Default served count is 117 after phase 73. |
| BND-06 all flags serve the roster | WIRED | `72-VERIFICATION.md` and `74-VERIFICATION.md`. Served set equals roster set, 154 names. Docs state the flag names and the counts. |
| BND-07 cron admin over the shared JobStore | WIRED | `73-VERIFICATION.md`. List, create, remove. Create and remove are approval-gated. |
| BND-08 learning surfaces and GoalStore | WIRED | `73-VERIFICATION.md`. `autolearn_turn`, `advisor_note`, `advisor_render`. GoalStore is `PrimeGoalStore` at `<root>/goals` through `goal_set`, `goal_pause`, `goal_resume`, `goal_clear`, `goal_status` when `prime.goals.enabled` is on. |
| BND-09 durable journal and status | WIRED | `73-VERIFICATION.md`. Cron jobs journal at `cron/turns.sqlite`. Delegate children share the parent journal. `durable_status` reports that cron journal. Write failure emits `prime_degraded` and the turn finishes. |
| BND-10 audit, archive, gates | WIRED | This file. Phase directories under `milestones/v14-phases/`. Final tree: pytest 1992 passed, mypy 327 files, ruff clean, evals 26, catalog and assemble exit 0, setup_check serves 117. |

## Flows

| Flow | Result |
|---|---|
| `/omega-doctor` through the host handler | The interceptor sees the inner `lead_doctor`. A rate limit or a missing roster entry denies the inner call before the tool runs. |
| Default host | Serves 117 roster tools. `rlm_*`, `agent_message_send`, and `agent_observe` are absent. Cron, learning, and `durable_status` are present. |
| `rlm` flag, no provider | `rlm_spawn` returns `not_configured: provider`. |
| `messaging` flag | `agent_message_send` from one session is visible to `agent_observe` on another session that shares the registry. |
| All seven Prime flags | Served names equal the 154 roster names. |
| Cron job then `durable_status` | The job's turn is in `cron/turns.sqlite`. `durable_status` reports `journal: present`. |

## Known limits

- No live Grok Bot account and no live model call. `delegate_task` and `rlm_spawn` return `not_configured: provider` without a provider env.
- Prime families stay off by default.
- The desk parent attaches its journal only when a child model exists, at the desk state path (`omega_prime/state/turns.sqlite`, or under `OMEGA_PRIME_STATE_DIR`). `durable_status` reads the cron journal (`cron/turns.sqlite`), not that desk file. If opening the desk journal raises, `parent.journal` stays `None` and delegate children run without one. Cron turns still emit `prime_degraded`.
- `VALIDATION.md` and `SECURITY.md` were not generated for phases 71–74.
- Dormant seeds and the archived v9 UAT were not acknowledged. They are not v14 requirements.
- This closeout does not commit or tag.
