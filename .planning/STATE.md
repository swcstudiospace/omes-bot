---
gsd_state_version: "1.0"
milestone: v11
milestone_name: Grok Bot native
current_phase: 63
current_phase_name: Seven enterprise improvements
status: executing
stopped_at: "Phase 62 complete and pushed to main (f2c33ed). Phase 63 Wave 1 (six parallel units) executing."
last_updated: "2026-10-09T10:55:00.000Z"
last_activity: 2026-10-09
last_activity_desc: Phase 62 verified and pushed (supply-chain CI green again); main's pre-existing red CI repaired (uninstallable lock, non-atomic job store); Phase 63 Wave 1 dispatched.
state_head: f2c33ed2badd90a76e1a720c4288b9532dcbf2e1
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 14
  completed_plans: 6
  percent: 43
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** One Omega Prime agent runs Hermes, Omp, and Prime in one
Python process, and one command attaches it to Grok Bot as a hardened tool host.
**Current focus:** Phase 63 - Seven enterprise improvements

## Current Position

Phase: 63 (Seven enterprise improvements) - EXECUTING
Status: Wave 1 of 3 running: streamable HTTP, scoped tokens, approval gateway, traffic protection, observability, deployment kit
Last activity: 2026-10-09 - Phase 62 closed (GRK-01..10 complete)

Phase completion: 1 of 2.

## Accumulated Context

### Decisions (v11, 2026-10-09)

- Source plan: the ultrathink graph `ut-mv0nfl17-58362dc4` (Linear SPE-8895..SPE-8900).
  It named a TypeScript layout because the planner could not see the repo; its structure
  (bootstrap/config, health probe, lifecycle, streaming engine, then seven improvements
  in four waves) is kept and translated onto the Python MCP host in `omega_prime/grokbot/`.
- Auth contract: static scoped bearer tokens (`read`, `call`, `admin`). The graph's
  HMAC-signed webhook ingress does not apply: Grok Bot reaches this host as an MCP client.
- Single seat: the graph's per-tenant sandbox maps to per-principal scopes.
- Reuse the MCP SDK's own transport security, body-size limit, session cap and session
  ownership instead of reimplementing them.
- No new third-party dependencies. Prometheus text and the token store are hand-written.
- Tool calls run in a worker thread behind a `ToolGate` (one at a time by default): before
  this, one slow tool froze health, keepalives and shutdown, and tools that call
  `asyncio.run` failed. Interceptors therefore run off the event loop and must be thread-safe.
- A token in a URL is never a credential, and uvicorn's access log drops query strings so a
  client that sends one cannot leak it into logs.
- Push policy: the user directed pushes to `main` with `prime-agent` as a git submodule
  (2026-10-09). Use explicit paths when staging; never stage the ignored upstream checkouts.
- Verification gates (every wave): `pytest omega_prime/tests`, evals runner,
  `assemble-prompts.sh --check`, `catalog --check`, `ruff check`, `ruff format --check`,
  `mypy omega_prime/`, `pyright` on changed files, docs tests, `pip-audit` on the lock.

### Decisions (v10, 2026-10-08)

- Architecture: behavior-port Prime's logic into `omega_prime/` Python.
  prime-agent has no PyO3/maturin bindings. The Rust workspace stays an
  ignored read-only checkout and CI-built parity oracle.
- Loop design: Prime joins the single conversation loop as a third logic
  source. Hermes and Omp were already one loop.
- License: AGPL-3.0, "Copyright (C) 2026 Spectrum Web Co". Ported Prime
  code keeps MIT attribution.
- Degradation: Prime families are default-off. Failures emit
  `prime_degraded` and the loop continues.
- Supply chain: pip-audit reads `requirements-lock.txt` and ignores
  PYSEC-2026-4114 (oauthlib authorization-server PKCE timing oracle;
  tweepy 4.17 pins `oauthlib<4`). Cargo dependabot is not used on the
  ignored pin; cargo-deny gates that workspace.
- User-approved exceptions (2026-10-09): LOOP-07 unmodified historical suite
  (376 passed / 2 inventory-pin failures), REPO-04 no Cargo Dependabot, CONN-01
  documented scope. No test was edited or shimmed.

### Prior milestone

v10 Prime merge closed 2026-10-09: 9 phases (53-61), 32/32 requirements
(30 wired, 2 user-approved exceptions), 0 open. See `.planning/milestones/v10-MILESTONE-AUDIT.md`.

### Blockers

None.

### Roadmap Evolution

- v11 Grok Bot native added 2026-10-09: Phase 62 (runtime completion) and Phase 63 (seven enterprise improvements)
- Merged Dependabot bumps had made `requirements-lock.txt` uninstallable (oauthlib 4 vs tweepy `<4`;
  huggingface-hub 2 vs tokenizers `<2`); restored and Dependabot now ignores those two majors.
  `JobStore._save` is atomic (an intermittent CI failure and a crash-corruption risk).

## Session

**Last session:** 2026-10-09T10:55:00.000Z
**Stopped at:** Phase 63 Wave 1 dispatched; Phase 62 closeout docs committed next.
**Resume file:** .planning/phases/63-grokbot-enterprise-improvements/63-CONTEXT.md
