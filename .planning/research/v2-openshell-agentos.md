# v2 research: OpenShell + AgentOS, and what Omega Prime borrows

Sources (fetched 2026-10-03):

- NVIDIA OpenShell README: https://github.com/NVIDIA/OpenShell
- NVIDIA technical blog: https://developer.nvidia.com/blog/add-runtime-controls-to-ai-agents-with-nvidia-openshell/
- Rivet AgentOS: https://rivet.dev/agentos

## OpenShell (Apache 2.0, v0.1.0)

Safe runtime for fleets of autonomous agents. Declare per-agent policy;
OpenShell enforces it outside the workload:

- Policy: filesystem, network, and process rules per agent.
- Kernel-level enforcement (Landlock LSM, Seccomp BPF); every network
  connection passes a policy check before leaving the sandbox.
- Credentials never visible to the agent; added only to requests bound for
  approved endpoints (providers).
- Policy prover: formal verification flags risky expansions (new host with
  credentials, new API method) for human review before a policy change lands.
- Policy advisor: approve new access just in time as the agent needs it.
- Control plane: Gateway (sandboxes, policy, access), Supervisor (inspects
  outbound requests against policy), Sandbox (isolation). Compute drivers
  for Docker and Kubernetes.

## AgentOS (Rivet)

OS-as-a-library per agent (WASM + V8 isolates instead of microVMs):

- Each agent and workflow run is a durable actor with SQLite state; accepted
  work recovers after interruption.
- Durable memory per session; session transcripts.
- Registry of agents, filesystems, browsers, software.
- Cron scheduling on actors with bounded execution history.
- MCP inspection of actor state, sessions, workflow runs.

## What v2 borrows (user-scoped: in-process only, single seat)

1. Declarative seat policy (tools, paths, network) enforced at dispatch,
   with an advisor diff that flags expansions — the OpenShell policy shape
   without kernel drivers or a fleet gateway.
2. Credential broker: keys from the environment, injected per approved
   endpoint, never in transcripts; secret redaction in events and logs.
3. Durable runs: SQLite turn journal with crash resume, cron execution
   history, checkpointed multi-step workflows — the AgentOS actor shape
   inside one process.
4. Real stdlib HTTP transport (retries, timeouts) enforcing the network
   allowlist, plus structured trace export.

## Explicitly out (user decision 2026-10-03)

- Container/namespace execution drivers; kernel-level enforcement.
- Fleet gateway, multi-seat registry, supervisor control plane.
- Formal policy prover (advisor diff only), MCP inspection server.
