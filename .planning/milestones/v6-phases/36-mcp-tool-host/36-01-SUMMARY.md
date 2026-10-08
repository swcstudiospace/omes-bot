# Summary 36-01: MCP server, profiles, host notes

## What shipped

`omega_prime/mcp_server.py` (new): the registry as an MCP stdio server on
the official SDK — `list_tools_handler` (registry schemas →
MCP Tools, roster-gated), `call_tool_handler` (dispatch with
`isError` on registry errors), `default_registry` (every family
with safe defaults; delegate skipped — needs a live parent
agent), `main` (`python -m omega_prime.mcp_server --root/--home`,
roster loaded from the shipped contract). No roster/policy
changes: the server exposes existing tools.

`omega_prime/tests/test_mcp_server.py` (new, 4 tests): list/call
handler behavior incl. roster filter + unknown/approval errors,
default registry serves the roster minus delegate, and a real
stdio roundtrip dogfooding the repo's own `mcp_session_call`.

`omega_prime/hosting/openshell/sandbox-policy.yaml` (new): genuine-schema
OpenShell profile (default-deny network, commented xAI stanza).
`omega_prime/hosting/agentos/NOTES.md` (new): honest notes (CPython
doesn't run in AgentOS VMs; host-beside-actor pattern).

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_mcp_server.py -q` → exit 0, 4 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 231 passed (227 + 4).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
