# Phase 57: Agent loop upgrade - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous

<domain>
## Phase Boundary

Upgrade the one conversation loop with Prime's loop-level capabilities:
persistent goals with budgets, session heartbeats, bounded autonomous mode
with quality gates, and agent-to-agent messaging — each behind a
default-off config flag, each failing loud-but-non-fatal, with
Hermes+Omp behavior bit-for-bit preserved when all flags are off.
In scope: `omega_prime/config.py` (new minimal config surface),
`omega_prime/agent/{goals,autonomous}.py` (new), `learning/goals.py`
extension, `cron/` heartbeat job kind, `tools/agent_message.py` (new),
loop wiring, regression fixture, tests. Out of scope: RLM tools (55),
harness (56), connector adapters (58), factory workflows.

</domain>

<decisions>
## Implementation Decisions

1. **Config surface (new, minimal):** `omega_prime/config.py` — stdlib
   json load of an optional `omega-prime.json` (the `SeatPolicy.load`
   precedent) plus `OMEGA_PRIME_*` env overrides. Shape:
   `{"prime": {"rlm": {"enabled": false}, "harness": {"enabled": false},
   "goals": {"enabled": false}, "heartbeat": {"enabled": false},
   "autonomous": {"enabled": false, "max_turns": N, "max_tokens": N,
   "max_minutes": N, "gate": "shell command"}, "messaging":
   {"enabled": false}}}`. All flags default off. Disabled family ⇒ tools
   not registered, prompt sections absent, loop hooks inert.
2. **Goals:** extend `learning/goals.py` (Omp objective+steps) with
   Prime's semantics (`pa-core/src/goals.rs`): objective validation,
   optional token budget with per-turn usage accrual
   (`goal_token_delta_for_usage`), turn-boundary continuation prompts
   (daemon `goal_continuation.rs` → Omega's turn finalizer seam),
   stale-active detection, completion report. Goal state persists via
   `durable/journal.py`.
3. **Heartbeats:** a new cron job kind that re-enters a named session
   with a prompt (Prime: `rlm-heartbeat` skill + `pa-core/src/cron/`).
   Rides the existing `cron/` scheduler + JobStore; fires serialized (v4
   rule).
4. **Autonomous mode:** `agent/autonomous.py` — an `AutonomousDriver`-style
   policy object consulted at turn finalization (Prime: engine holds no
   autonomous logic; the host drives). Budgets: max turns / tokens /
   minutes, normalized at start; quality gate = a shell command run via
   the terminal tool with a retry window; gate failure steers the loop
   with the failure text; hitting a limit stops cleanly with a structured
   reason. Prime's honest semantics are preserved verbatim: **a passed
   gate checks only what that gate verifies; reaching a limit does not
   imply task success.**
5. **Agent messaging:** `tools/agent_message.py` + an in-process session
   registry. Family view: parent / direct children / siblings (Prime's
   roster join collapses — Omega is single-process, so the registry is
   the truth). `agent_message_send` + `agent_observe` tools; delivery is
   direct; a missing recipient is a structured error, never a silent drop.
6. **Degraded mode (LOOP-06):** every Prime loop hook is wrapped; a hook
   raising/timing out logs a structured `prime_degraded` event (family,
   error, turn id) to the audit log and the loop continues without that
   family for the turn.
7. **Regression parity (LOOP-07):** a transcript fixture test —
   scripted-model loop run recorded pre-v10 (existing test suite passes
   unmodified is the primary gate; the fixture adds an explicit
   golden-transcript comparison with all flags off).

</decisions>

<code_context>
## Existing Code Insights

- Loop extension points (overlap map §2): harness events/beforeModelCall,
  turn finalizer, modes wrapper, curator post-turn hook.
- `agent/budget.py`: per-turn iteration budget — autonomous budgets wrap,
  not replace, it.
- `cron/scheduler.py` + JobStore: job kinds are registered; a heartbeat
  kind is additive.
- `durable/journal.py`: SQLite turn journal — goal/autonomous state rides
  it.
- `session/persist.py`: named session persistence — messaging registry
  builds on it.
- Prime sources: `pa-core/src/goals.rs`, `pa-core/src/autonomous/`
  (driver/gates), `pa-core/src/cron/`, `pa-daemon/src/agent_messaging*.rs`,
  `pa-cli/src/print_autonomous.rs` (continuation shape: turn_end →
  turn_start with a continuation user row, no run boundary).

</code_context>

<specifics>
## Specifics

**New tools:** `goal_set/pause/resume/clear/status` (family `goal`),
`heartbeat_set/list/clear` (family `heartbeat`), `autonomous_start/status/
stop` (family `autonomous`), `agent_message_send`, `agent_observe`
(family `messaging`). Writes ⇒ `requires_approval`.

**Tests:** `test_goals_prime.py` (budget accrual, continuation,
stale-active, completion), `test_heartbeat.py` (cron re-entry of a named
session), `test_autonomous.py` (budget stop, gate pass/fail paths, retry
window, clean limit stop), `test_agent_message.py` (send/observe, family
view, missing-recipient error), `test_prime_config.py` (flags default
off, disabled ⇒ absent from roster/prompt), `test_prime_degraded.py`
(hook failure ⇒ structured event + loop continues),
`test_prime_regression.py` (flags-off transcript fixture).

**Acceptance:** v10-REQUIREMENTS LOOP-01..07; full suite + evals +
assemble check green.

</specifics>
