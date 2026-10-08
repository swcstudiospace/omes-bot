# Tool host

Run the real Omes tools behind your bot over MCP.

## The server

```bash
.venv/bin/python -m omes.mcp_server --root . [--home ~] [--no-roster]
```

`--root` is the repo checkout (default: cwd). Without
`--no-roster` the server exposes exactly the shipped roster —
108 tools. `delegate_task` is excluded: it needs a live parent
agent, so orchestration stays in the bot, not behind MCP.

Policy and approval denials come back as MCP error results with
the registry's own text. Approval-gated tools (deploys,
publishes, merges, tracker writes) stay gated: pre-approve in
the host process or call them from a session that approves.

The host speaks MCP spec `2026-07-28` via the v2 Python SDK
(`mcp>=2,<3`): snake_case in Python (`is_error`,
`input_schema`), camelCase on the wire. Raw wire payloads
(Greptile KB client, scripted peers) stay camelCase.

`substrate_docs_search` returns extracted, redacted excerpts with bounded
document/dataset metadata and citation provenance, not the raw retrieval
response. A valid empty search returns `chunks: []`; an unconfigured or
malformed docs response returns an error.

## OpenShell

Prefer running the host sandboxed. NVIDIA OpenShell
(`omes/hosting/openshell/sandbox-policy.yaml`) confines the
server: workdir included, repo readable, writes to scratch,
network default-deny (the shipped Omes network allowlist is
empty — open hosts explicitly per install).

```bash
openshell sandbox create --name omes \
  --policy omes/hosting/openshell/sandbox-policy.yaml \
  --no-auto-providers
```

## Egress Hardening & Browser Confinement

Browser and preview operations require strict egress enforcement:

- Destination transport (`DestinationTransport` in `omes/providers/destination.py`)
  enforces seat-level network policy (`SeatPolicy`). All DNS answers are resolved,
  classified, and validated; unlisted hosts or private/loopback/link-local/multicast IP
  addresses fail safe before any socket dial.
- Direct dialed connections verify TLS peer identities strictly, enforcing single-exchange
  request budgets, exact Content-Length framing, and chunked transfer decoding limits.
- Sandboxed browser sessions (`GuardedBrowserFactory` in `omes/tools/browser_egress.py`)
  require verified kernel confinement, cgroup accounting, and persistent socket tracking.
  In environments without verified kernel sandbox readiness, browser launches fail closed.
- Preview and review orchestration (`WebClient` in `omes/tools/webpack.py`) binds an explicit
  root operation, draining all in-flight scopes and validating terminal accounting receipts
  prior to publication or vision model analysis.

## AgentOS

Rivet AgentOS VMs run Wasm/V8 and do not run CPython, so the
host does not execute inside an AgentOS actor. Run the host on a
VM, VPS, or sandbox and have the actor reach it over MCP or
HTTP. Details: `omes/hosting/agentos/NOTES.md`.
