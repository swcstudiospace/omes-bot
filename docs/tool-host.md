# Tool host

Run the real Omes tools behind your bot over MCP.

## The server

```bash
.venv/bin/python -m omes.mcp_server --root . [--home ~] [--no-roster]
```

`--root` is the repo checkout (default: cwd). Without
`--no-roster` the server exposes exactly the shipped roster —
103 tools. `delegate_task` is excluded: it needs a live parent
agent, so orchestration stays in the bot, not behind MCP.

Policy and approval denials come back as MCP error results with
the registry's own text. Approval-gated tools (deploys,
publishes, merges, tracker writes) stay gated: pre-approve in
the host process or call them from a session that approves.

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

## AgentOS

Rivet AgentOS VMs run Wasm/V8 and do not run CPython, so the
host does not execute inside an AgentOS actor. Run the host on a
VM, VPS, or sandbox and have the actor reach it over MCP or
HTTP. Details: `omes/hosting/agentos/NOTES.md`.
