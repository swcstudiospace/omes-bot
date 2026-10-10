# Phase 72 Plan: Family reachability

**Requirements:** BND-05, BND-06.

## Task (single agent; mcp_server registration + tests + proof + docs)

1. In `default_registry`, behind the existing `prime_enabled(config, "rlm")`
   and `prime_enabled(config, "messaging")` checks, register both families:
   rlm with the host's `_DeskParent` (verify `require_parent` contract; write
   a thin adapter if the RLM parent contract differs from delegate's — one
   adapter over the same model/tools, not a second implementation), messaging
   with session name `bot-00-omega-prime`. Update the stale comment block.
2. Tests (new file `omega_prime/tests/test_prime_family_serving.py`):
   - default registry (flags off): none of the 9 names served; count 110.
   - `OMEGA_PRIME_PRIME_RLM_ENABLED=1` (or config json equivalent): the 7
     `rlm_*` names appear in `registry.schemas()` and dispatch returns
     explicit `not_configured`-style dicts without credentials, never an
     exception.
   - messaging flag on: `agent_message_send`/`agent_observe` served; send
     between two session names round-trips through the shared registry.
3. Proof: all seven `OMEGA_PRIME_PRIME_<FAMILY>_ENABLED=1` + `setup_check
   --root .` serves exactly the 147 roster names (set equality, not count).
   Record the command and output in the verification.
4. Docs truth: any doc claiming rlm/messaging cannot serve through the host
   gets corrected; state the flag names. Regenerate the tool catalog the
   normal way if it is generated.

## Acceptance

- Flags off ⇒ served count still 110 (composition tests unchanged).
- Flags on ⇒ 147/147, roster == served set equality.
- No doc left claiming the two families are unservable.

Skip full gates; orchestrator runs them.
