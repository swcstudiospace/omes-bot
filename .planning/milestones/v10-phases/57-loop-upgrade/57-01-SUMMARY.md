# Phase 57 — Agent loop upgrade — SUMMARY

## What was done

Ported Prime Agent's loop-level capabilities into Omega Prime's single
conversation loop as pure Python (behavior port, per the v10 architecture
decision). Each family sits behind a default-off config flag
(`omega_prime/config.py`, Phase 55 surface); with all flags off the loop and
the default registry are bit-for-bit the pre-v10 behavior (LOOP-07).

Source contracts @ `967eb13f` (MIT, PrimeIntellect — see VENDOR.md):
`pa-core/src/goals.rs`, `pa-core/src/autonomous/`, `pa-core/src/cron/`,
`pa-daemon/src/agent_messaging*.rs`, `pa-cli/src/print_autonomous.rs`.

New modules:

- `omega_prime/agent/goals.py` — `PrimeGoalStore` extends the Omp
  `learning/goals.py` `GoalStore` with Prime's semantics: objective
  validation, an optional token budget with per-turn usage accrual, a
  turn-boundary `continuation_prompt`, stale-active detection, and a
  completion report. Prime state rides a `prime_goal.json` sidecar next to
  the Omp goal file, so pre-v10 goal files load unchanged.
- `omega_prime/agent/autonomous.py` — `AutonomousDriver` + `AutonomousBudget`.
  Budgets (max turns / tokens / minutes) are normalized at start; the quality
  gate is a shell command run via `tools/terminal.run_terminal` with a retry
  window; gate failure steers the loop with the failure text; hitting a limit
  stops cleanly with a structured reason. Prime's honest semantics are kept
  verbatim: a passed gate checks only what that gate verifies, and reaching a
  limit does not imply task success.
- `omega_prime/agent/messaging.py` — `SessionRegistry` + frozen `AgentMessage`
  (verbatim Prime field names). Prime's roster join (parent / children /
  siblings) collapses to registry membership: Omega is single-process, so the
  in-process registry is the truth. Delivery is direct; a missing recipient
  (or sender) is a structured error, never a silent drop (LOOP-04).
- `omega_prime/agent/degraded.py` — `guarded_hook` (LOOP-06): every Prime loop
  hook runs wrapped; a hook that raises emits a structured `prime_degraded`
  event (family, error, turn id — redacted like every event) via
  `agent/harness.emit` and the loop continues without that family for the
  turn. Loud-but-non-fatal: the failure is always recorded, never swallowed.
- `omega_prime/cron/heartbeat.py` — a `HEARTBEAT_KIND` cron job that re-enters
  a named session with a prompt. Rides the existing `cron/scheduler.py`
  `JobStore`; fires serialized per the v4 rule.

Tool families (writes approval-gated, reads not):

- `tools/goals.py` — `goal_set/pause/resume/clear/status`
- `tools/heartbeat.py` — `heartbeat_set/list/clear`
- `tools/autonomous.py` — `autonomous_start/status/stop`
- `tools/agent_message.py` — `agent_message_send`, `agent_observe`

Wiring (the tool-family recipe):

- `contracts/tool-rosters/omega-prime.yaml` — appended the 13 names after the
  harness names; header comment updated.
- `contracts/policies/omega-prime.json` — added the 13 names to the allowlist.
- `tooling/catalog.py` — added Goals / Heartbeat / Autonomous / Messaging to
  FAMILIES; regenerated `docs/tool-catalog.md`.
- `mcp_server.py` `default_registry` — registers goals, heartbeat, and
  autonomous when their config flags are on. Messaging is skipped there (it
  needs a live session name, like `delegate_task` needs a live agent).
- `setup_check.py` — the four families added to the gated set.
- Drift-guard tests updated: `test_tools.py`, `test_growth.py`,
  `test_providers.py` (roster concatenation + registration),
  `test_mcp_server.py` (gated set).

## Deviations from the plan

- `test_prime_config.py` already existed from Phase 55 and covers the config
  surface generically over `PRIME_FAMILIES` (all six families), so no new
  config test was needed.
- `messaging.py` `observe()` originally snapshotted inbox dicts before
  marking messages read, so observed messages reported `read: false`; fixed
  to mark-then-snapshot (caught by `test_agent_message.py`).
- The regression gate is explicit rather than a recorded golden transcript:
  `test_prime_regression.py` runs a scripted-model loop with all flags off
  and asserts zero `prime_*` events plus a default registry containing no
  Prime tool names; the unmodified pre-v10 suite passing remains the primary
  gate.

## Validation evidence

- `pytest omega_prime/tests/test_goals_prime.py test_heartbeat.py
  test_autonomous.py test_agent_message.py test_prime_degraded.py
  test_prime_regression.py` — 45 passed (12 + 7 + 10 + 9 + 5 + 2).
- `pytest omega_prime/tests` (full suite) — 484 passed (439 pre-Phase 57;
  +45).
- `python -m omega_prime.evals.runner omega_prime/evals/cases` — 26 passed,
  0 failed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` — up to date.
- `python -m omega_prime.tooling.catalog --check` — up to date.
- `python -m omega_prime.setup_check --root .` — registry serves 108 roster
  tools (Prime families gated off by default).
- `ruff check omega_prime/` + `ruff format --check` — clean.
- `mypy omega_prime/` — no issues in 202 source files.

## Acceptance criteria

- Persistent goals with budgets, continuation prompts, stale detection,
  completion report (LOOP-01) — met.
- Session heartbeats via the cron scheduler (LOOP-02) — met.
- Bounded autonomous mode with budgets and a shell quality gate, honest stop
  semantics (LOOP-03) — met.
- Agent-to-agent messaging with structured missing-recipient errors
  (LOOP-04) — met.
- All families default-off config-gated (LOOP-05) — met.
- Degraded mode: hook failure ⇒ structured `prime_degraded` event, loop
  continues (LOOP-06) — met.
- Flags-off regression: no Prime events, no Prime tools, pre-v10 suite
  unmodified (LOOP-07) — met.
