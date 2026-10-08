---
phase: 53-prime-discovery
plan: 01
subsystem: research
tags: [prime-agent, capability-map, parity-baseline, vendor-pin]
provides:
  - Prime capability map with file-cited must-preserve behaviors
  - Omega Prime overlap map with integration points
  - Rust workspace parity baseline + upstream pin
affects: [54-rust-ci, 55-rlm-recursion, 56-continual-harness, 57-loop-upgrade, 58-connectors]
key-files:
  created:
    - .planning/research/v10-prime-capability-map.md
    - .planning/research/v10-omega-overlap-map.md
    - .planning/milestones/v10-ROADMAP.md
    - .planning/milestones/v10-REQUIREMENTS.md
    - .planning/phases/53-prime-discovery/53-CONTEXT.md
    - .planning/phases/53-prime-discovery/53-01-PLAN.md
  modified:
    - .planning/ROADMAP.md
    - .planning/STATE.md
    - .planning/PROJECT.md
    - VENDOR.md
    - .gitignore
---

# Phase 53 summary

Prime Agent is mapped for the merge. The capability map
(`.planning/research/v10-prime-capability-map.md`) covers the twelve
capability families — RLM recursion (spawn/collect/list/delete/
create_session/progress_note/rename with verbatim signatures and closed
status vocabularies), persistent REPL semantics, the continual harness +
/refine (evidence-required refinement events, local-default scoping,
snapshots), goals with token budgets, heartbeats/schedules, bounded
autonomous mode with quality gates, agent-to-agent messaging, compaction
arms, executable skills, daemon supervision + session persistence,
system-prompt layering, and factory workflows — each cited to its source
`crate::module` or `rlm/` module with must-preserve behaviors and an
Omega Prime merge target. The overlap map
(`.planning/research/v10-omega-overlap-map.md`) names the exact
integration points: the tool-family recipe (registry → `*_TOOL_NAMES` →
roster yaml → drift-guard tests), the loop extension seams (harness
events, turn finalizer, modes wrapper, curator hook), the config gap
(no central settings module — v10 introduces `omega_prime/config.py`),
and the durability story.

Milestone scaffolding landed: v10 ROADMAP (phases 53–60), REQUIREMENTS
(26), STATE (gsd-tools-recognized), PROJECT evolution + decisions, and
the `VENDOR.md` pin: prime-agent @
`967eb13fd488507af5f590e9c6ea8b2672f1fc05` (2026-10-07, MIT), ignored
checkout like hermes-agent/oh-my-pi.

## Key finding: no PyO3 boundary exists

Prime Agent's Rust↔Python wiring is a spawned-kernel process boundary
(pa-core kernel manager boots a venv + IPython kernel running the
`prime-agent-runtime` rlm package over NDJSON stdio, protocol v3) — no
pyo3/maturin/uniffi/cffi anywhere in the workspace manifests. Combined
with Omega Prime's one-Python-process rule, the merge is a behavior port
with the Rust workspace as the CI-built parity oracle (Phase 54), and
"connectors" are typed Python adapters (Phase 58).

## Verification

Command: `cargo test --workspace --locked` (prime-agent/, cargo 1.98.1 /
rustc 1.98.1)
Exit code: 101 — 622 passed, 3 failed, all three in
`pa-cli --test acp_mode_e2e`:
`acp_prompt_settles_after_rlm_quiescence`,
`acp_cancel_during_settle_cancels_the_subagents`,
`acp_eof_during_settle_exits_and_leaves_resident_subagents`
(ACP-stdio settle/timeout assertions; pa-cli is out of v10 port scope —
daemon/CLI are not ported). Reproduced under full parallelism; see
54-CONTEXT for the CI treatment (documented exclusion set with reason,
per prime-agent AGENTS.md).

Command: `.venv/bin/python -m pytest omega_prime/tests -q`
Exit code: 0 (`378 passed`)

Command: `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases`
Exit code: 0 (`26 passed`)

Command: `bash omega_prime/scripts/assemble-prompts.sh --check`
Exit code: 0

Unverified: the acp_mode_e2e trio under `--test-threads=1` (timing-sensitivity
confirmation rerun in flight at phase close; result recorded in Phase 54
CONTEXT before the CI job lands).

## Deferred

- Frame-level NDJSON protocol read (`repl.md` beside `repl.py`) — deferred
  to Phase 55 only if the port needs frame detail (in-process port likely
  does not).
- Factory spec schema detail (4.7k-line `rlm/factory.py`) — read when the
  factory core is ported (post-55).
