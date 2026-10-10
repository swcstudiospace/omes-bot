# Phase 71 Context: Core/boundary inversion repair

**Requirements:** BND-01, BND-02, BND-03, BND-04.

Evidence from the 2026-10-10 boundary map (scout reports, file:line verified):

1. `omega_prime/agent/runtime.py:18` imports `parse_omega_command` from
   `omega_prime.grokbot.commands`. The intercept itself already dispatches
   through `self.registry.dispatch("omega_command", ...)`; only the parser
   import crosses the layer line.
2. `omega_prime/tools/omega_command.py:13` imports `execute_command` from
   `omega_prime.grokbot.commands` — a core registry family reaching into the
   boundary package.
3. `omega_prime/mcp_server.py` imports the private `grokbot._io`.
4. Nested dispatch bypass: `grokbot/commands.py` `_tool` (235-249) and
   `grokbot/workflows.py` `dispatch_tool` call `registry.dispatch` directly.
   Registry gates (policy/approval/audit) apply, but the host-side roster
   membership check and the per-principal interceptor chain (scope, audit
   digest, in-flight, rate limit; `grokbot/remote.py:443-456`) do not. An
   external caller passes all of those; a workflow step invoked by that same
   caller passes none.
5. `mcp_server.roster_names` (106-121) hand-parses the roster YAML; tests
   re-implement the same parsing. Two parsers is one too many contracts.

The slash-command engine (catalog, parser, executor, workflows, seed file) is
registry orchestration — application core, not transport. The `grokbot/`
package keeps transport and bot ops only.
