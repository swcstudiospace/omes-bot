# Summary 42-01: Graph ops + store-lock guard

## What was built

- Client graph ops: `graph_claim` (lease dict), `graph_release`/
  `graph_complete` (raw text via `_call_tool_text`), `graph_heartbeat`;
  shared `_mcp_post` round trip; all fail-closed with input validation.
- Four graph tools (`claim`/`release`/`complete`/`heartbeat`) in the
  substrate family with schemas, error mapping, and approval flags on the
  three shared-state mutations; roster + policy extended (109 tools).
- `omega_prime/tests/test_store_lock.py`: import guard (no DB/redis drivers) +
  endpoint guard (no backing-store hosts/URLs/ports) + assertion that the
  `systems.py` injected seams stay `None` by default.

## Verification

`.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 288 passed
(281 carried + 7 new). No network in tests. No new dependencies.
