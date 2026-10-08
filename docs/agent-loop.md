# The agent loop

Omega Prime runs one conversation loop — the Hermes loop with the Omp
harness merged in — and, from v10, Prime Agent's loop-level capabilities.
All Prime families are **config-gated, default off**; with every flag off
the loop behaves exactly as pre-v10 (pinned by
`tests/test_prime_regression.py`).

## What each Prime family adds

- **Goals** (`prime.goals.enabled`) — a persistent goal (objective +
  ordered steps) survives across turns until completed, paused, or cleared.
  Optional token budget with per-turn accrual; while the goal is active,
  unfinished, within budget, and not stale, the loop is steered with a
  continuation prompt at the turn boundary. State rides a
  `prime_goal.json` sidecar, so pre-v10 goal files load unchanged.
  Tools: `goal_set`, `goal_pause`, `goal_resume`, `goal_clear`,
  `goal_status`.
- **Heartbeats** (`prime.heartbeat.enabled`) — a cron job kind that
  re-enters a named session with a prompt on schedule, riding the existing
  scheduler; fires are serialized. Tools: `heartbeat_set`,
  `heartbeat_list`, `heartbeat_clear`.
- **Autonomous mode** (`prime.autonomous.enabled`) — a driver consulted at
  turn finalization with normalized budgets (max turns / tokens / minutes)
  and a quality gate: a shell command (argv list, never a shell string) run
  via the terminal tool with a retry window. Gate failure steers the loop
  with the failure text; hitting a limit stops cleanly with a structured
  reason. Honest semantics, verbatim from Prime: **a passed gate checks
  only what that gate verifies; reaching a limit does not imply task
  success.** Tools: `autonomous_start`, `autonomous_status`,
  `autonomous_stop`.
- **Agent messaging** (`prime.messaging.enabled`) — named sessions exchange
  messages through an in-process registry; a missing recipient is a
  structured error, never a silent drop. Tools: `agent_message_send`,
  `agent_observe`.
- **RLM recursion** (`prime.rlm.enabled`) — spawn/collect child agents
  mid-turn with Prime's handle shapes, closed status sets, and progress
  notes (512 UTF-16 code-unit cap, 10s throttle). See the tool catalog.
- **Continual harness** (`prime.harness.enabled`) — `/refine` applies
  small, evidence-backed updates to supplemental harness state (prompts,
  memories, skill descriptions, subagent specs) with snapshots and exact
  rollback; the immutable base system prompt is never rewritten.

## Degraded mode

Every Prime loop hook runs wrapped (`agent/degraded.py::guarded_hook`). A
hook that raises emits a structured `prime_degraded` event — family, error,
turn id, redacted like every event — and the loop continues without that
family for the turn. Loud-but-non-fatal: the failure is always recorded,
never swallowed.

## Configuration

`omega-prime.json` at the repo root, or
`OMEGA_PRIME_PRIME_<FAMILY>_ENABLED=1` per family (env beats file):

```json
{
  "prime": {
    "rlm": { "enabled": false },
    "harness": { "enabled": false },
    "goals": { "enabled": false },
    "heartbeat": { "enabled": false },
    "autonomous": { "enabled": false, "max_turns": 12, "max_tokens": 200000,
                    "max_minutes": 30, "gate": ["pytest", "-q"] },
    "messaging": { "enabled": false }
  }
}
```

A disabled family is not registered, not on the roster, and not in the
prompt. Write tools in every enabled family require approval; reads do not.
