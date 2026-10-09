# ADR 0002: Load the pinned Prime runtime and crates in-process

- **Status:** accepted (2026-10-08)
- **Deciders:** Spectrum Web Co
- **Supersedes:** the "never imported at runtime" consequence in
  [ADR 0001](0001-prime-merge-architecture.md). ADR 0001 still rejects a
  sidecar daemon and a second agent process.

## Context

v10 ported Prime's differentiating families into `omega_prime/` Python and
left the pinned checkout as a CI oracle. That is not the whole of Prime
Agent. The checkout still holds nine Rust crates and the `rlm` kernel
(`factory`, `repl`, `bash`, `harness`, `mcp`, and the skill packages). The
product was only calling the ports.

## Decision

Omega Prime stays one Python process. When `prime.kernel.enabled` is on
(default off, same gate style as the other Prime families):

- The process imports the pinned `rlm` package from
  `prime-agent/prime-agent-runtime/src`. Sources are not copied and the
  checkout is not patched.
- `rlm.repl.host_request` is answered in-process by `InProcessHost`, which
  drives the existing `RlmHost`. Factory, bash, and cell execution call the
  real modules.
- Skill packages under `prime-agent/skills/*/src` are imported from that
  tree.
- `native/omega-prime-prime` is a PyO3 cdylib. Python calls the Rust
  implementations of goal validation and state, autonomous run accounting,
  REPL protocol 3, heartbeat schedules, refinement history, and the
  `/goal` and `/autonomous` parsers. `prime_goal` and `prime_autonomous`
  are those calls. `crates.probe` also calls each workspace member:
  telemetry catalog, incident worker ids and `JsNumber`, provider overflow
  detection and JSON repair, model-catalog compatibility, tool-argument
  validation, private-frame encoding and the durable create command,
  session search, and CLI mode names. It does not start the TUI or a
  daemon worker. Until that extension is built, `prime_crates` reports the
  nine workspace members and `loaded: false`, and the two command tools
  raise `ImportError`.

Flags off leave the default registry and the pre-v10 loop unchanged.

Native provider selection is separate from the kernel-tool gate:
`OmegaPrimeAgent.from_prime` constructs `PrimeProviderModel`, which calls
`ai.complete` / `pa_ai::complete_simple` from the existing Python conversation
loop. `ai.resolve_models` calls Prime's actual catalog resolver. Both use the
same extension; no second loop or agent process is started.

Real registry schemas are offered to the model, and returned calls dispatch
through the registry's policy and approval checks. Raw Prime assistant wire
messages remain in durable `prime_message` metadata so signatures and response
IDs survive replay. Missing extension/credentials and terminal provider failures
raise errors; they do not fall back to a Python provider.

The reusable Tokio runtime has two async workers and at most four blocking
workers. The bridge releases the GIL during waits. `timeoutMs` covers the full
completion and session-gate wait; cancellation has a one-second settlement
grace. Codex cached connections share their original cancellation token under
a bounded per-session gate. Unsettled cancellation is reported explicitly
and prevents unsafe reuse; Prime's private provider tasks cannot be forcibly
aborted through its public API.

This integrates the native provider path, not the complete Prime application.
`pa-agent`'s own loop, `pa-core`'s `SessionEngine`, native TUI ownership, and the
daemon supervisor are not substituted for Omega's loop or session machinery.


## Consequences

- A missing checkout or an unbuilt extension is an explicit error on the
  kernel tools, not a silent reimplementation.
- The Rust parity workflow still tests the checkout. This ADR does not
  change the pin, the three ACP skips, or the local ext4 hazards.
- `pa-cli` and `pa-tui` are called as libraries (mode names, missing-subsystem
  text, session search). They are not the product UI or a second
  `prime-agent` process. `pa-daemon` is called for frame encoding and the
  durable create command. It does not spawn workers.
