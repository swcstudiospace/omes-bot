# Phase 53: Prime discovery + parity baseline - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous (gsd-autonomous; decisions recorded from ultrathink gate with evidence-adjusted defaults)

<domain>
## Phase Boundary

Map every Prime Agent capability that v10 will port, pin the upstream
checkout, and establish the Rust workspace's own test suite as the green
parity baseline — before any porting begins. In scope: the two research
maps, the VENDOR pin, the cargo baseline. Out of scope: any porting, any
CI changes, any `omega_prime/` edits.

</domain>

<decisions>
## Implementation Decisions (milestone-level, recorded 2026-10-08)

1. **Architecture: behavior port into Python.** Prime Agent
   (`prime-agent/`, github.com/PrimeIntellect-ai/prime-agent @
   `967eb13fd488507af5f590e9c6ea8b2672f1fc05`, MIT) has NO PyO3/maturin/
   uniffi/cffi bindings — verified by grep over all crate manifests. Its
   Rust↔Python wiring is a spawned-kernel process boundary: pa-core's
   kernel manager boots a venv + IPython kernel running the
   `prime-agent-runtime` `rlm` package and speaks wire-protocol frames to
   it. Omega Prime's standing rule (PROJECT.md, v1) is one Python process;
   Omp's Rust crates were likewise left unported with behavior ported.
   Therefore: Prime's differentiating logic is behavior-ported into
   `omega_prime/`; the Rust workspace stays an ignored read-only checkout
   and serves as the CI-built parity oracle; "connectors" are typed Python
   adapter modules exposing ported capabilities through registry/roster.
2. **Loop design: capability merge into the single loop.** Hermes and Omp
   are already one merged loop (v1 Phase 7), not two runtime agents.
   Prime joins as a third logic source: RLM spawn/collect extends
   `agent/delegate.py`, /refine extends `agent/curator.py`, autonomous
   mode as a mode, heartbeats extend `cron/`, agent messaging as tools.
3. **License: AGPL-3.0.** "Copyright (C) 2026 Spectrum Web Co",
   SPDX-License-Identifier: AGPL-3.0-only headers on new source files.
   Ported Prime code retains MIT attribution per VENDOR.md. Supersedes the
   v6 MIT decision by explicit user request (2026-10-08).
4. **Degradation: degrade-with-warning.** Prime capability families are
   default-off config flags; a disabled or failed family logs a loud
   structured warning and the loop continues; with all flags off,
   Hermes+Omp behavior matches pre-v10 exactly (regression fixture).
5. **Leftover milestones: none.** v1–v9 verified complete (ROADMAP empty,
   STATE complete, 372 tests + 26 evals + all gates exit 0). v10 starts on
   that green baseline.

### User's verbatim intent

"we should have a nice port of the Rust into this … an intelligent and
complete merge because Prime Agent has some really powerful logic … Build
and integrate all the crates and build the connectors. Ensure we've
upgraded the agent loop … Hermes, Omp and Prime all in a Bot."

</decisions>

<code_context>
## Existing Code Insights

**Prime Agent checkout (`prime-agent/`, read-only):**
- Rust workspace, 9 crates, dependency direction pinned in its AGENTS.md:
  pa-types/pa-telemetry/pa-agent (leaves) ← pa-ai ← pa-models ← pa-core ←
  pa-daemon; pa-tui depends on pa-types alone; pa-cli is the composition
  root. Workspace lints: pedantic clippy at warn, `unsafe_code` forbidden.
- `pa-agent`: provider-independent turn loop (`run_loop`, `ToolDispatcher`
  trait) — the "powerful logic" core.
- `pa-core`: session engine — RLM kernel lifecycle (spawn/execute/revive
  IPython), tools (bash/edit/ipython), skills loading, system-prompt
  assembly, compaction, harness refinement, autonomous mode, goals, cron
  job store, MCP host side, settings.
- `pa-daemon`: supervisor (one worker per session), session registry,
  agent-to-agent messaging bridge, append-only JSONL session store,
  archiving.
- `prime-agent-runtime/src/rlm/` (Python, ~11.8k lines): the kernel-side
  runtime — `rlm.spawn/collect/list_subagents/delete_subagent/
  create_session/progress_note`, harness CRUD + refine, bash, MCP client,
  skill loading. This package is the most direct behavior spec for the
  port: it is already Python.
- Surface contract (its AGENTS.md): tools `bash`/`edit`/`ipython`; RLM
  kernel API; layered system prompt (static layers + dynamic tail +
  `[harness-digest]` user message).

**Omega Prime (`omega_prime/`, the merge target):**
- Single loop: `agent/conversation_loop.py` + turn phases; Omp harness
  merged (`agent/harness.py`: events, steering, pause, budget,
  speculative execution).
- Existing analogs to extend: `agent/delegate.py` (isolated children,
  background handles), `agent/curator.py` (post-turn learning), `cron/`
  (scheduler re-entry), `agent/modes.py` (plan mode), `durable/`
  (SQLite journal), `memory/`, `skills_runtime/`, `tools/registry.py` +
  `contracts/tool-rosters/omega-prime.yaml` (drift-guarded roster).
- Gates: `.venv/bin/python -m pytest omega_prime/tests -q` (372),
  `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases`
  (26), `bash omega_prime/scripts/assemble-prompts.sh --check`, ruff,
  mypy, setup_check, catalog --check.

</code_context>

<specifics>
## Specifics

**Research artifacts being produced this phase:**
- `.planning/research/v10-prime-capability-map.md` — per-capability:
  source crate::module, public API, must-preserve behaviors (file-cited),
  merge target, overlap notes.
- `.planning/research/v10-omega-overlap-map.md` — Omega Prime integration
  points: registry/roster/prompt/loop-phase/config/durability, with the
  v4/v5 tool-family recipe.

**Parity baseline:** `cargo test --workspace --locked` in `prime-agent/`
on the ambient toolchain (cargo 1.98.1, rustc 1.98.1). Log at
`/tmp/v10-cargo-baseline.log`; the passing result + toolchain versions are
recorded in the phase SUMMARY.

**Acceptance bar (from v10-ROADMAP):** both maps landed with file-cited
behaviors; cargo baseline exits 0; VENDOR.md pin recorded (done this
phase: remote, commit, license, scope).

</specifics>

<relevant_files>
## Relevant Files

Read-only sources:
- `prime-agent/AGENTS.md`, `prime-agent/Cargo.toml`
- `prime-agent/crates/pa-agent/src/agent_loop/`
- `prime-agent/crates/pa-core/src/session_engine/`, `kernel/`, `autonomous/`, `goals.rs`, `cron/`, `refinement/`, `skills/`, `prompts/`
- `prime-agent/crates/pa-daemon/src/` (supervisor, agent_messaging)
- `prime-agent/prime-agent-runtime/src/rlm/*.py`

Merge target (read-only this phase):
- `omega_prime/agent/`, `omega_prime/tools/registry.py`,
  `omega_prime/contracts/tool-rosters/omega-prime.yaml`, `omega_prime/cron/`,
  `omega_prime/durable/`, `omega_prime/learning/`

Written this phase:
- `.planning/research/v10-prime-capability-map.md`
- `.planning/research/v10-omega-overlap-map.md`
- `VENDOR.md` (pin — already landed)
- `.gitignore` (`/prime-agent/` — already landed)

</relevant_files>
