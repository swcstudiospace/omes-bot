# Summary 36-01: MCP server, profiles, host notes

## What shipped

`omes/mcp_server.py` (new): the registry as an MCP stdio server on
the official SDK — `list_tools_handler` (registry schemas →
MCP Tools, roster-gated), `call_tool_handler` (dispatch with
`isError` on registry errors), `default_registry` (every family
with safe defaults; delegate skipped — needs a live parent
agent), `main` (`python -m omes.mcp_server --root/--home`,
roster loaded from the shipped contract). No roster/policy
changes: the server exposes existing tools.

`omes/tests/test_mcp_server.py` (new, 4 tests): list/call
handler behavior incl. roster filter + unknown/approval errors,
default registry serves the roster minus delegate, and a real
stdio roundtrip dogfooding the repo's own `mcp_session_call`.

`omes/hosting/openshell/sandbox-policy.yaml` (new): genuine-schema
OpenShell profile (default-deny network, commented xAI stanza).
`omes/hosting/agentos/NOTES.md` (new): honest notes (CPython
doesn't run in AgentOS VMs; host-beside-actor pattern).

## Verification

- `.venv/bin/python -m pytest omes/tests/test_mcp_server.py -q` → exit 0, 4 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 231 passed (227 + 4).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
