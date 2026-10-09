---
gsd_state_version: "1.0"
milestone: v12
milestone_name: Programming Desk merge
current_phase: 66
current_phase_name: Grok Bot clone-and-run proof
status: in_progress
stopped_at: "Phase 64 complete (DESK-01..04, DESK-08). 1916 passed. Phase 65 next."
last_updated: "2026-10-09T22:10:00.000Z"
last_activity: 2026-10-09
last_activity_desc: Phase 64 desk runtime activation verified (1916 passed, mypy clean).
state_head: 5934ff9
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 0
  completed_plans: 0
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** One Omega Prime agent runs Hermes, Omp, and Prime in one Python process, and one command attaches it to Grok Bot as a hardened tool host.
**Current focus:** v12 Programming Desk merge — the seven-seat desk runtime real under one bot (subbots via delegate_task/RLM), receipts machine-checked, gates targeting the work repo, Grok Bot native end to end.

## Current Position

Phase: 66 (Grok Bot clone-and-run proof) - IN PROGRESS
Status: v12 scoped 2026-10-09 (REQUIREMENTS/ROADMAP; SEED-005 evidence 8/8 CONFIRMED-GAP)
Last activity: 2026-10-09 - v11 archive; v12 scoping

Phase completion: 2 of 4 (64-65 done).

## Accumulated Context

### Decisions (v12, 2026-10-09)

- Source: `/root/src/repos/programming-desk` @ `9de3aa3` (seven-seat desk OS). Merge direction
  (user, 2026-10-09): behavior-port the pattern under Omega Prime — one bot controlling
  subbots — Grok Bot native; no second gateway deployment, no new third-party dependencies.
- SEED-005 re-verified on the current tree: 8/8 claims CONFIRMED-GAP (empty desk seams,
  install-vs-work root, `delegate_task` unserved, lead pass test-only, self-referential gates,
  self-attested receipts + self-approval deadlock, five missing service clients, no desk
  config surface). Evidence: `phases/64-desk-runtime-activation/64-CONTEXT.md`.
- Install root vs work root split is additive; default work root = install root (today's
  behavior unchanged).
- Substrate mediation stays; Tailscale forwarders default; no Railway resource changes
  (user decisions 2026-10-07).

### Decisions (v11, 2026-10-09)

- Source plan: the ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900), translated from its
  TypeScript layout onto the Python MCP host in `omega_prime/grokbot/`.
- Auth: static scoped bearer tokens (`read`, `call`, `admin`) replace the graph's HMAC webhook ingress; per-principal
  scopes replace tenant sandboxes (single seat).
- Reuse the MCP SDK's transport security, body limit, session cap and session ownership; no new third-party dependencies.
- Tool calls run in a worker thread behind one `ToolGate` (serial by default). Interceptors run off the event loop and are thread-safe.
- Interceptor order: observers (audit, metrics) before every denying interceptor, because `run_tool_call` stops at the
  first denial and runs `after` only for interceptors whose `before` ran.
- A token in a URL is never a credential and never reaches a log: uvicorn's access log is replaced by a middleware that
  never records a query string or headers.
- Default limits are generous (600 requests/min, 300 tool calls/min per principal).
- Dependabot ignores the `oauthlib` and `huggingface-hub` major bumps until `tweepy` and `tokenizers` relax their pins.
- Push policy: pushes to `main` with `prime-agent` as a git submodule were directed by the user on 2026-10-09. Stage with
  explicit paths; never stage the ignored upstream checkouts. No tags.
- Verification gates: `pytest omega_prime/tests`, evals runner, `assemble-prompts.sh --check`, `catalog --check`,
  `setup_check`, `ruff check`, `ruff format --check`, `mypy omega_prime/`, `pyright` on changed files, `actionlint`,
  `docker build --check`, `pip-audit` on the lock, and a real run of the image.

### Decisions (v10, 2026-10-08)

- Architecture: behavior-port Prime's logic into `omega_prime/` Python. prime-agent has no PyO3/maturin bindings. The Rust
  workspace stays an ignored read-only checkout and CI-built parity oracle.
- Loop design: Prime joins the single conversation loop as a third logic source.
- License: AGPL-3.0, "Copyright (C) 2026 Spectrum Web Co". Ported Prime code keeps MIT attribution.
- Degradation: Prime families are default-off. Failures emit `prime_degraded` and the loop continues.
- Supply chain: pip-audit reads `requirements-lock.txt` and ignores PYSEC-2026-4114 (oauthlib authorization-server PKCE
  timing oracle; tweepy 4.17 pins `oauthlib<4`). Cargo dependabot is not used on the ignored pin; cargo-deny gates that workspace.
- User-approved exceptions (2026-10-09): LOOP-07 unmodified historical suite (376 passed / 2 inventory-pin failures),
  REPO-04 no Cargo Dependabot, CONN-01 documented scope. No test was edited or shimmed.

### Prior milestones

v12 Programming Desk merge scoped 2026-10-09 (4 phases 64-67, 13 requirements; in progress).
v11 Grok Bot native closed 2026-10-09: 2 phases (62-63), 17/17 requirements, 0 open. v10 Prime merge closed 2026-10-09:
9 phases (53-61), 32/32 requirements (30 wired, 2 user-approved exceptions).

### Blockers

None.

### Roadmap Evolution

- v11 Grok Bot native added 2026-10-09: Phase 62 (runtime completion) and Phase 63 (seven enterprise improvements); both complete.
- Pre-existing breakage on `main` repaired: merged Dependabot majors had made `requirements-lock.txt` uninstallable;
  `JobStore._save` is now atomic (an intermittent CI failure and a crash-corruption risk).
- Archived 2026-10-09 on user confirmation ("Ensure we completely complete our
  Milestone"): `.planning/phases/62-*` and `63-*` moved to `milestones/v11-phases/`,
  requirements archived as `milestones/v11-REQUIREMENTS.md`, roadmap collapsed with
  the v11 section captured in `milestones/v11-ROADMAP.md`.

## Session

**Last session:** 2026-10-09T13:05:00.000Z
**Stopped at:** Phase 64 verified; Phase 65 next.
**Resume file:** .planning/phases/64-desk-runtime-activation/64-VERIFICATION.md
