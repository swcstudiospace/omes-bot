# ADR 0001: Prime merge architecture — behavior port, not embedding

- **Status:** accepted (2026-10-08, milestone v10)
- **Deciders:** Spectrum Web Co
- **Supersedes:** the v6 single-seat MIT decision (license only; see below)

## Context

Omega Prime already merges two upstream agent runtimes — Hermes Agent (the
conversation loop) and oh-my-pi / Omp (the harness: events, steering,
budget, compaction) — into one Python process. Milestone v10 adds a third:
Prime Agent, a Rust workspace (`prime-agent/`, pinned in `VENDOR.md` at
`967eb13f`) with a Python kernel runtime. The question: how does Prime's
logic join the agent?

Options considered:

1. **FFI embedding** (PyO3/maturin/uniffi/cffi): build the Rust crates as a
   Python extension and call across the boundary.
2. **Sidecar process**: run the Prime daemon beside Omega Prime and bridge
   over its NDJSON/ACP protocols.
3. **Behavior port**: port Prime's capability semantics into
   `omega_prime/` Python, keep the Rust workspace as a CI-built parity
   oracle, and expose the ported capabilities through typed connector
   adapters (`omega_prime/prime/`).

## Decision

**Behavior port (option 3).** Verified fact that decides it: the pinned
prime-agent checkout contains **no PyO3, maturin, uniffi, or cffi wiring** —
its Rust↔Python boundary is a spawned-kernel NDJSON process protocol, not
an in-process FFI surface. There is nothing to embed; embedding would mean
writing a brand-new FFI layer upstream never designed. A sidecar breaks the
v1 rule (one Python process, no sidecars) and adds a daemon lifecycle the
product does not otherwise need.

Consequences:

- The Rust workspace stays an ignored, read-only checkout; CI
  (`rust-parity.yml`) builds and tests it at the pinned commit as the
  parity oracle, with cargo-deny for license compliance. It is never
  imported at runtime.
- Each ported capability family (RLM recursion, continual harness, goals,
  heartbeats, autonomous mode, agent messaging) lands as pure Python behind
  a default-off config flag (`omega-prime.json`); with all flags off the
  pre-v10 behavior is bit-for-bit preserved (LOOP-07 regression tests).
- The "connectors" of the merge are typed Python adapters
  (`omega_prime/prime/`) with versioned schemas — the typed boundary
  between the tool surface and the capability modules, not a wire protocol.
- Fidelity is pinned by behavior-parity fixtures (`omega_prime/tests/parity/`)
  derived from the Rust/Python sources with per-fixture source citations.

## License consequence

v10 relicenses the repository from MIT to **AGPL-3.0-only**,
`Copyright (C) 2026 Spectrum Web Co`, by explicit owner request
(2026-10-08). Ported upstream code retains its MIT attributions in module
docstrings and `VENDOR.md`; new source files carry
`SPDX-License-Identifier: AGPL-3.0-only` headers.

## Alternatives rejected

- **FFI embedding** — no upstream FFI surface exists; would require
  designing and maintaining one.
- **Sidecar daemon** — violates the one-process rule; doubles the
  operational surface for zero capability gain.
- **Vendoring Prime's Python runtime wholesale** — its runtime assumes the
  daemon supervisor; the port keeps the wire vocabulary (field names,
  closed status sets, error strings) on Omega Prime's own concurrency
  primitives instead.
