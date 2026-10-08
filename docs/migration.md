# Migrating to v10 (Prime merge)

v10 merges a third upstream runtime — Prime Agent — into Omega Prime and
relicenses the repository. It is designed to be a no-op upgrade for
existing installs.

## If you upgrade and change nothing

- **Behavior is unchanged.** Every Prime capability family is a config
  flag, default off. With all flags off, the loop, roster, prompt assembly,
  and tools are bit-for-bit the pre-v10 behavior (regression-pinned by
  `tests/test_prime_regression.py`: no `prime_*` events, no Prime tools in
  the default registry, the pre-v10 suite passing unmodified).
- **Your data is unchanged.** Goal state, memory, sessions, and cron jobs
  load as before; Prime goal semantics live in a `prime_goal.json` sidecar
  that does not touch the base `goals.json` schema.

## The license change

The repository moves from MIT to **AGPL-3.0-only**, Copyright (C) 2026
Spectrum Web Co. If you embed Omega Prime in a service, review the AGPL's
network-use terms. Upstream-ported modules keep their MIT attributions
(`VENDOR.md`); the relicensing applies to Omega Prime itself.

## Opting in to Prime capabilities

Set flags in `omega-prime.json` (repo root) or via
`OMEGA_PRIME_PRIME_<FAMILY>_ENABLED=1` env vars — see
[agent-loop.md](agent-loop.md) for the full reference and per-family tool
lists, and [connectors.md](connectors.md) for the typed adapter contracts
(versioned schemas, strict decoding, structured errors).

New rostered tool families when enabled: `rlm_*` (7), `harness_*` (6),
`goal_*` (5), `heartbeat_*` (3), `autonomous_*` (3), `agent_message_send` +
`agent_observe` (2). All are in the policy allowlist; writes require
approval.

## For downstream redistributors

- The Rust workspace (`prime-agent/`) is an ignored, read-only parity
  oracle — never shipped, never imported. Nothing about packaging changes:
  `pip install -e .` remains the whole install.
- If you pinned the MIT license for compliance, pin the pre-v10 release;
  v10 and later are AGPL-3.0-only.
