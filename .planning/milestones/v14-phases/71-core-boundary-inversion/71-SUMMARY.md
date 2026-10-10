---
status: complete
requirements_completed: [BND-01, BND-02, BND-03, BND-04]
---

# Phase 71 Summary: Core/boundary inversion repair

**Requirements:** BND-01, BND-02, BND-03, BND-04. All wired.

The slash engine lives in `omega_prime/commands/`. `agent/runtime.py` imports `parse_omega_command` from there. `tools/omega_command.py` imports `execute_command` from there. The seed file is `omega_prime/commands/seeds/memory.txt`. Nothing under `omega_prime/agent/` or `omega_prime/tools/` imports `omega_prime.grokbot`.

`grokbot/_io.py` is now the public module `omega_prime/tooling/fs.py`. `mcp_server` reads a token file through `read_secret_file`. The grokbot package imports the same module. No file imports `grokbot._io`.

Roster names come from one parser, `roster_names` / `load_roster_names` in `omega_prime/tooling/roster.py`. `mcp_server`, `setup_check`, the catalog, and the family-serving tests call it.

When a host `tools/call` runs, `call_tool_handler` sets a context-var dispatcher. `dispatch_tool` uses it, so an `omega_command` step re-enters that call's roster check and interceptor chain. In-process callers (no scope set) still use `registry.dispatch`. A third nested re-entry returns `nested_dispatch_depth`.
