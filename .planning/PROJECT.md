# Omega Prime

## What This Is

Omega Prime is one Grok programming bot (`swcstudiospace/omega-prime`). It ports the Hermes Agent runtime and the oh-my-pi agent harness into a single Python agent, then exposes that agent the way programming-desk exposes a seat: a prompt that points at a skills folder, a tool roster, and a prompt folder. The upstream checkouts in this directory (hermes-agent, oh-my-pi) and `~/src/repos/programming-desk` and `~/src/repos/claude-ultrathink` are read-only sources. The bot lives under `omega_prime/`.

## Core Value

One Omega Prime agent runs both agents' logic — loops, subagents, tools, skills, memory, and the rest of each runtime — so later tools, connectors, skills, memories, and routines have a real agent to attach to.

v2 milestone: that same agent, hardened the way OpenShell and AgentOS harden theirs — a declarative seat policy enforced at dispatch, a credential broker that keeps secrets out of transcripts, durable runs that resume after a crash, and real transports with structured traces. Still one in-process Python agent with one seat.

v3 milestone: that hardened agent as a working Grok Bot — an X connector tool family with approval-gated publishing, an engagement sweep routine producing queued drafts, nightly learning through the curator, and an eval harness with CI.

v4 milestone: that bot wired to third-party libraries as real pip dependencies — a tweepy X transport, an official-SDK MCP session client, PyRIT red-team depth, an APScheduler scheduler backend, and Telegram/Discord connectors. This reverses the v1–v3 "no new third-party dependencies" rule by explicit user decision (2026-10-03); the Hermes/Omp no-vendor no-import rule still stands.

v5 milestone: the entire Programming Desk absorbed into Omega Prime with Omega Prime as Lead — desk seats become domain packs (skills + tool families + routines + roster entries) in the one agent, and interactive browser/device review lands behind the vision and browser transports. User decisions (2026-10-03): lead+packs over a multi-seat port, entire-desk scope, interactive (not screenshot-only) device review. Ground truth: `.planning/codebase/`.

v6 milestone: Omega Prime as a Grok Bot Add-Bot product — Omp magic keywords in the loop, ultrathink natively integrated (prompt routines + CLI bridge, no AGPL vendoring), an MCP tool host installs can attach, a clean template + setup flow, and docs structured for GitBook Git Sync. User decisions (2026-10-03): hybrid architecture (template + optional tool host), MIT license, full milestone scope. Ground truth: `.planning/research/v6-runtime-spike.md`.

v7 milestone: Omega Prime as a substrate surface — the Grok Bot briefs on open, emits its turn/tool trail with graph provenance, shares memory through substrate-mcp, recalls episodes from the shared `ultrathink` Hindsight bank, and answers docs from RAGflow, while GreptimeDB/TimescaleDB/DragonflyDB stay behind the store lock. User decisions (2026-10-03): substrate-mediated direction, shared bank, fakes + opt-in live probes. Ground truth: `~/src/repos/agent-substrate` governance + grokbot loop docs, Hindsight OpenAPI v0.9.1.

v8 milestone: public launch — branded README, standard public-repo files, richer GitBook docs with a CI-kept tool catalog, Greptile connected with repo review standards, and a KB sync pipeline publishing Greptile's knowledge base into the docs. User decisions (2026-10-03): connect Greptile now, push branch + open PR, GitBook stays the host. Ground truth: Greptile docs corpus (config + KB MCP tools).

v9 milestone: SOTA upgrade — the same one-agent product brought to state-of-the-art engineering and agent standards: in-flight hardening landed, lint + types enforced in CI, pinned dependencies, current provider/protocol wire formats, and a deeper hermetic eval battery. User decisions (2026-10-07): full-SOTA scope, land the dirty tree first, hermetic verification stays (live probes manual opt-in).

v10 milestone: Prime merge — the third agent joins. Prime Agent (`prime-agent/`, PrimeIntellect, MIT, pinned `967eb13f`) contributes its differentiating logic — RLM subagent recursion (`rlm.spawn`/`collect`), the continual harness (`/refine` with snapshots and rollback), goals/heartbeats/autonomous mode, and agent-to-agent messaging — behavior-ported into the one Python agent per the v1–v9 precedent. The Rust workspace stays as an ignored read-only checkout and CI-built parity oracle. The repo relicenses to AGPL-3.0 (Spectrum Web Co 2026) and hardens to enterprise open-source standards. User decisions (2026-10-08): behavior-port architecture (no PyO3 boundary exists upstream; one-Python-process rule stands), capability-merge loop design, AGPL-3.0 relicense, degrade-with-warning for Prime capability failures.

## Current Milestone: v10 Prime merge

**Goal:** Merge Prime Agent into Omega Prime as the third logic source — behavior-faithful ports of its differentiating capabilities, typed connector adapters, an upgraded loop, and an enterprise-grade AGPL-3.0 repository.

**Target features:**
- Discovery: capability map + overlap map + green Rust parity baseline
- Rust workspace in CI as the parity oracle (pinned toolchain, locked deps, license gate)
- RLM recursion port: spawn/collect/list/delete/create_session/progress_note
- Continual harness port: /refine, harness state, snapshots, rollback
- Loop upgrade: goals, heartbeats, autonomous mode, agent messaging; default-off config flags; degraded mode; Hermes+Omp regression parity
- Connector layer: typed adapters, contract tests, failure injection, parity fixtures
- Repo hardening: AGPL-3.0, root files, docs, supply-chain CI

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [x] Single-seat Grok shell: directives, prompt, roster, template, deterministic assemble
- [x] Hermes conversation loop and turn phases, with the prompt, steer, compression, and interrupt invariants
- [x] Tool registry and the coding toolset
- [x] Remaining Hermes agent tools (code execution, MCP, browser, approvals, plugins)
- [x] Skills, memory, session search, and the curator
- [x] Delegation and cron re-entering the same agent
- [x] Omp harness behavior merged into that same loop
- [x] Omp edit pipeline, LSP, and DAP
- [x] Sessions, tasks, modes, plan mode, extensions, autolearn, goals, advisor, exec, and agent-side security
- [x] One memory store that serves both call shapes
- [x] Provider surface with a Grok adapter, and a Grok Bot template that matches what is actually registered

### Out of Scope

- Temporal as the way the two agents are merged — one Python process is the merge; Temporal can be a later durability adapter
- A sidecar that calls the Hermes checkout and the Omp checkout — both runtimes are ported, not wrapped
- Product chrome: Hermes TUI, desktop, website, locales, packaging, messaging gateways, Feishu, Yuanbao, Home Assistant, Spotify, kanban UI; Omp TUI, collab web, stats site, CLI gallery, Rust crates, bazel and nix packaging
- Pushing this repository or opening a GitHub repo from this milestone
- Provisioning a Grok Bot account — the template markdown is what a person pastes into Share → Create template
- Seven-seat desk rules (channel size, QUALITY off-channel, cross-seat intake). `ownership.yaml` stays so the tree can grow later

## Context

programming-desk (`/root/src/repos/programming-desk`) is the pattern: shared core directives prepended to one bot XML, the XML pointing at `skills/.../SKILL.md` and `contracts/tool-rosters/<seat>.yaml`, and `grokbot/templates/<SEAT>.md` carrying name, description, enabled skills, and routines with no prompt body and no tokens. Hermes is Python. Omp is TypeScript plus Rust. The agent logic is what this milestone ports. Languages differ, so the host is Python: Hermes is moved and adapted, Omp is a behavior port checked against its TypeScript tests.

Pinned reads (see `VENDOR.md`): Hermes `1a4508e2aff2db5f50409893a2115be777bd5643`, oh-my-pi `0e2411c0df59fce8c56dc03a5f1c9afffcb0d746`. Both MIT.

## Constraints

- **Repo boundary**: This git root is `/root/src/repos/omega`. Do not commit into `/root/src/repos` (`swcstudiospace/repos`). Do not push.
- **Runtime**: One Python process. No Node or Rust agent process beside Omega Prime. No new global toolchain.
- **Sources**: Do not vendor, subtree, or runtime-import `hermes-agent/` or `oh-my-pi/`.
- **Verification**: A completion claim needs a command and an exit code (programming-desk PD-1). No secrets (PD-4). No destructive operation without recorded approval (PD-5).
- **Providers**: A missing xAI key does not fail the milestone. The Grok adapter is tested with a fake transport.
- **Done means parity**: A phase is done when its parity checks pass, not when a scaffold exists.

## Environment Facts

- Planning root and code repo: `/root/src/repos/omega-prime`; current branch
  `v6-grok-ship`, HEAD `79ff51a`. v9 is committed and clean. v10 phase commits
  are expected (convention: `Phase NN: …` messages; `Refs SPE-XXXX` trailers
  allowed). Never commit the `prime-agent/` checkout itself (ignored upstream,
  like `hermes-agent/` and `oh-my-pi/`). Do not push, merge, or tag without
  explicit user request.
- GSD CLI: `node /root/.hermes/gsd-core/bin/gsd-tools.cjs`, run from this repo.
  Existing reports use body-only `**Status:**` fields; the CLI requires leading
  YAML frontmatter. Repair the artifacts, not the installed GSD tools.
- Repo virtualenv: `.venv/bin/python` is Python 3.12.3; `.venv/bin/ruff` is
  0.16.10; `.venv/bin/mypy` is 2.4.0. No install or global toolchain is needed.
- Parent baseline on 2026-10-07: `.venv/bin/python -m pytest omega_prime/tests -q`
  passed 352 tests with no skips. `.venv/bin/python -m omega_prime.evals.runner
  omega_prime/evals/cases` passed 26 evals. Use a fresh HOME and XDG_DATA_HOME beneath
  `$TMPDIR` (`/root/.hermes/cache/scratch`) for verification; keep real HOME
  `/root` for GSD/role discovery and do not use `/tmp/fakehome`.
- Other parent baseline gates, all exit 0: `bash
  omega_prime/scripts/assemble-prompts.sh --check`, `.venv/bin/ruff check omega_prime/`,
  `.venv/bin/ruff format --check omega_prime/` (206 files), `.venv/bin/mypy omega_prime/`
  (175 source files), `.venv/bin/python -m omega_prime.setup_check --root .`, and
  `.venv/bin/python -m omega_prime.tooling.catalog --check`.
- Setup smoke check serves 108 roster tools over MCP; optional ultrathink and
  substrate connections remain unconfigured. The milestone is hermetic;
  unconfigured live services are not evidence of live verification.
- Config retains auto_advance=true, skip_discuss=true, text_mode=true,
  use_worktrees=false, ui_phase=false, ui_review=false, commit_docs=false,
  and git.create_tag=false. Review, Nyquist, and security hooks are active.
  Cleanup/moving phase directories requires separate user confirmation.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| One Python process, one OmegaPrimeAgent | The user wants both agents' logic merged into one bot, not a router in front of two checkouts | — Pending |
| Hermes is move-and-adapt; Omp is a behavior port into that same agent | The loop already exists in Python. Omp's TypeScript tests are the spec for harness behavior | — Pending |
| Temporal is deferred | It was a candidate because the languages differ. It is not required to call the port done | — Pending |
| Milestone discuss is the approved plan | Re-asking the merge would stall a decision that is already made | ✓ Good |
| Product chrome stays out unless a phase's own tests cannot pass without it | The milestone is the agent, not the apps wrapped around it | — Pending |
| Grok shell stays in step with the registry | The roster is the index of tools actually registered. The template lists only skills and routines that exist on disk | — Pending |
| v2 stays in-process and single-seat | Container drivers and a fleet gateway are deferred; policy, broker, durability, and transports land first | — Pending |
| v4 uses real pip dependencies for third-party integrations | User chose pip deps over in-house ports for tweepy, MCP SDK, PyRIT, APScheduler, aiogram, discord.py (2026-10-03) | — Pending |
| v5 absorbs the desk as lead + domain packs | User chose one Omega Prime Lead with packs over a 7-seat port, entire-desk scope, interactive device review (2026-10-03) | ✓ Good |
| v6 ships the Add-Bot product on the hybrid runtime | Spike proved Grok Bot runs on xAI's computer and templates don't carry secrets/MCP; user approved template + optional MCP host (2026-10-03) | ✓ Good |
| v6 integrates ultrathink without vendoring; Omega Prime is MIT | claude-ultrathink is AGPL-3.0; user chose MIT + prompt/bridge integration (2026-10-03) | ✓ Good |
| swcstudiospace/omega-prime is the real repo | User created it 2026-10-03; history pushed there, old PR #2 closed as superseded | ✓ Good |
| v7 integrates substrate-mediated, not direct clients | Store lock + governance: only substrate-mcp touches Greptime/Timescale/Dragonfly; Omega Prime is a surface (user chose 2026-10-03) | ✓ Good |
| v7 shares the `ultrathink` Hindsight bank | One set of episodic beliefs across the ultrathink system; no silos (user chose 2026-10-03) | ✓ Good |
| v7 verifies with fakes + opt-in live probes | Committed tests stay hermetic; read-only Railway probes run manually, never in CI (user chose 2026-10-03) | ✓ Good |
| v8 launches public with Greptile connected | User chose connect-now, push + PR, GitBook + verify CI (2026-10-03); init blocked on org app install (user step), KB enrollment stays a Greptile-contact ask | ✓ Good |
| v9 upgrades to SOTA in place | User chose full-SOTA scope, land dirty tree first, hermetic verification stays (2026-10-07); one-agent architecture and Add-Bot unwired compat unchanged | ✓ Good |
| v10 ports Prime behavior into Python; Rust stays as parity oracle | prime-agent has no PyO3/maturin bindings (spawned-kernel process boundary); one-Python-process rule and the v1–v9 port precedent stand (2026-10-08) | — Pending |
| v10 merges Prime as capabilities in the single loop | Hermes+Omp are already one merged loop; Prime joins as a third logic source, not a separate runtime agent (2026-10-08) | — Pending |
| v10 relicenses to AGPL-3.0 (Spectrum Web Co 2026) | Explicit user request (2026-10-08); supersedes the v6 MIT decision; ported Prime code keeps MIT attribution | — Pending |
| v10 degrades with warning on Prime capability failure | Prime families are default-off flags; Prime-disabled behavior matches pre-v10 exactly (2026-10-08) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-07 after v9 milestone start (SOTA upgrade; defining requirements)*
