# Spike Manifest

## Ideas

### omega-native-integrations
Omega Prime (formerly Omes Bot; the Grok Bot, Python/pip, MIT, single agent process) must connect natively to Agent Substrate, Agent Swarm and Claude Ultrathink. It must also run the Programming Desk as a 1-Bot Programmer, verify code itself, use NVIDIA OpenShell and rivet.dev AgentOS, and drive Cursor Cloud Sessions with Ultrathink uplift before launch and code review after. These spikes de-risk the highest-uncertainty integrations before the Omega milestone is planned (seeds SEED-002, SEED-006, SEED-007, SEED-012).

**Requirements:**

- Keep substrate mediation for GreptimeDB/TimescaleDB/DragonflyDB. The v7 store-lock test stays (user decision).
- The AgentOS integration is an optional TypeScript sidecar that Omega calls over HTTP. CPython never runs inside AgentOS (user decision).
- Each Cursor Cloud launch requires human approval (user decision).
- No Railway resource changes, global installs, or AGPL code copying.
- Substrate MCP calls must use the MCP SDK Streamable HTTP client (auto/legacy mode, protocol 2025-11-25) and treat is_error as failure (spike 001).
- OpenShell gates must report "unavailable", never "passed", when the gateway or supervisor runtime is unhealthy, and must use sandbox names of 19 characters or fewer (spike 002).
- The AgentOS sidecar is installed on demand (about 2.1 GB), with pinned versions, and is used only for JS/TS execution and type-checks, never as the security boundary (spike 003).

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | omega-native-integrations | substrate-streamable-http | standard | Given the running local substrate-mcp on 127.0.0.1:7410, when Omega Prime's current SubstrateClient MCP shape and the official MCP Python SDK Streamable HTTP client each initialize, list tools and call one tool, then the current shape fails as research predicts while the SDK client negotiates, lists tools and surfaces isError correctly | VALIDATED | substrate, mcp, streamable-http |
| 002 | omega-native-integrations | openshell-verification-sandbox | standard | Given openshell 0.1.2 and Docker on this host, when a sandbox created from a deny-network policy runs pytest on a copied sample repo, then exit code and output return to the host, network and out-of-scope writes are denied, and the sandbox is removed afterwards | PARTIAL (host gateway supervisor image missing) | openshell, sandbox, verification |
| 003 | omega-native-integrations | agentos-sidecar | standard | Given Node and @rivet-dev/agentos-core, when a minimal Node sidecar exposes exec and typecheck over HTTP and a Python client calls it, then a VM runs a JS snippet and returns stdout/exit, and TS type errors come back as diagnostics | VALIDATED (caveats: 2.1 GB install, beta security) | agentos, rivet, sidecar, typescript |
