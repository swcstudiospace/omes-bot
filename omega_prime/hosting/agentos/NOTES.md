# AgentOS host notes

AgentOS (Rivet) VMs are lightweight in-process OS instances on Wasm
and V8, one Rivet Actor per agent. CPython does not run inside them,
so the Omega Prime tool host (`python -m omega_prime.mcp_server`) does not execute
inside an AgentOS actor.

Supported patterns today:

1. **Omega Prime beside AgentOS.** Run the tool host on a VM, VPS, or
   OpenShell sandbox (see `../openshell/sandbox-policy.yaml`) and
   have the AgentOS actor reach it over MCP stdio (same machine) or
   HTTP. The actor owns orchestration; Omega Prime owns tools.
2. **Revisit on Python/WASI.** If a supported Python runtime for the
   AgentOS VM appears, the host entrypoint stays the same
   (`omega_prime.mcp_server:main`); only the packaging changes.

No AgentOS APIs are invented here. When wiring pattern 1, follow
the rivet-dev/agentos docs for actor setup and outbound calls.
