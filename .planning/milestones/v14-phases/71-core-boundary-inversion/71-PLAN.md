# Phase 71 Plan: Core/boundary inversion repair

**Requirements:** BND-01, BND-02, BND-03, BND-04.

## Wave 1 (parallel, disjoint files)

**Task A — slash engine to core.** Move `grokbot/commands.py` and
`grokbot/workflows.py` (and the seed file `grokbot/seeds/`) into a new core
package `omega_prime/commands/`. Update every importer: `agent/runtime.py`,
`tools/omega_command.py`, tests, docs paths. No behavior change; no shims.

**Task BD — host hygiene.** Make the `grokbot._io` helper used by
`mcp_server` public in the layer that should own it. Extract the roster
parser into one shared function; `mcp_server` and tests use it.

## Wave 2 (after A; consumes the new module home)

**Task C — nested dispatch through the boundary gates.** When `omega_command`
arrives through the host, its inner tool calls re-enter the host's roster +
interceptor chain for the calling principal (contextvar-based dispatch
closure set by the host call path; plain `registry.dispatch` fallback
in-process). Tests: recording interceptor sees inner calls; over-quota
principal limited on the inner call; roster-absent tool denied.

## Acceptance

- `grep -rn "omega_prime\.grokbot" omega_prime/agent omega_prime/tools` → empty.
- No private `grokbot._io` import in `mcp_server`; one roster parser repo-wide.
- New nested-dispatch tests pass; existing omega_command/intercept tests pass.
- Full gates green (orchestrator runs them once after wave 2).
