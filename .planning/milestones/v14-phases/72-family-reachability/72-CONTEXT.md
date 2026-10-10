# Phase 72 Context: Family reachability

**Requirements:** BND-05, BND-06.

`omega_prime/contracts/tool-rosters/omega-prime.yaml` lists 37 gated Prime
names (rlm 7, harness 6, goals 5, heartbeat 3, autonomous 3, messaging 2,
kernel 11). `mcp_server.default_registry` registers only five of the seven
families behind their flags. The comment in `mcp_server.py` (~646-656) says
RLM "needs a live parent agent, so registration happens where the agent's
registry is built (skipped here)" and messaging "needs a session name, so it
registers where the agent's registry is built (skipped here)" — but
`default_registry` IS where the registry is built, and nothing else registers
them. Result: `OMEGA_PRIME_PRIME_RLM_ENABLED=1` serves nothing; the flag and
the roster names are dead contract.

Facts that make registration possible today:

- `_DeskParent` (mcp_server.py 215-241) is the in-process parent used by
  `delegate_task`: `child_model` runs child turns through the provider env,
  `tools` maps registered names to registry dispatch, `max_depth=2`,
  `max_children=1`. `tools/rlm.py register_rlm_tools(registry, parent,
  enabled=..., run_child=..., session_store=...)` validates the parent via
  `agent/rlm.py require_parent` — the executor verifies contract fit and
  adapts (thin adapter, not a second parent implementation).
- `tools/agent_message.py register_messaging_tools(registry, session,
  enabled=..., session_registry=...)` needs one session name; the seat id
  `bot-00-omega-prime` is the single-process identity.
- Both families answer `not_configured` style results without credentials —
  no exception paths (family docstrings assert this).

BND-06 closes the loop: all seven flags on ⇒ host serves exactly the 147
roster names; `setup_check` proves roster == served.
