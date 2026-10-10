# Phase 66 port evidence

File locations for the three sources behind the programming desk. This note does not record command results.

## Hermes

The conversation loop lives in `omega_prime/agent/`, including `omega_prime/agent/conversation_loop.py`.

## Omp

- Roster: `omega_prime/contracts/tool-rosters/omega-prime.yaml` and `omega_prime/grokbot/rosters/default.json`
- Policy: `omega_prime/policy/policy.py`
- Registry: `omega_prime/tools/registry.py` (`ToolRegistry`); the host builds the served set in `omega_prime/mcp_server.py` (`default_registry`)

## Prime

- `omega_prime/prime/`
- `omega_prime/prime_kernel/`
- `omega_prime/tools/rlm.py`
- `omega_prime/tools/goals.py`
- `omega_prime/tools/heartbeat.py`
- `omega_prime/tools/autonomous.py`
- `omega_prime/tools/agent_message.py`
- `VENDOR.md`
- `omega_prime/contracts/prime-agent.pin.json`

Prime families stay off by default. `delegate_task` is served. Without a provider env it returns `not_configured: provider`. The served count is the roster intersection `setup_check` reports (109 today).
