# Omes Bot

## What This Is

Omes Bot is one Grok programming bot. It ports the Hermes Agent runtime and the oh-my-pi agent harness into a single Python agent, then exposes that agent the way programming-desk exposes a seat: a prompt that points at a skills folder, a tool roster, and a prompt folder. The two upstream checkouts in this directory are read-only sources. The bot lives under `omes/`.

## Core Value

One Omes agent runs both agents' logic — loops, subagents, tools, skills, memory, and the rest of each runtime — so later tools, connectors, skills, memories, and routines have a real agent to attach to.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [x] Single-seat Grok shell: directives, prompt, roster, template, deterministic assemble
- [x] Hermes conversation loop and turn phases, with the prompt, steer, compression, and interrupt invariants
- [x] Tool registry and the coding toolset
- [ ] Remaining Hermes agent tools (code execution, MCP, browser, approvals, plugins)
- [ ] Skills, memory, session search, and the curator
- [ ] Delegation and cron re-entering the same agent
- [ ] Omp harness behavior merged into that same loop
- [ ] Omp edit pipeline, LSP, and DAP
- [ ] Sessions, tasks, modes, plan mode, extensions, autolearn, goals, advisor, exec, and agent-side security
- [ ] One memory store that serves both call shapes
- [ ] Provider surface with a Grok adapter, and a Grok Bot template that matches what is actually registered

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

- **Repo boundary**: This git root is `/root/src/repos/Omes-Bot`. Do not commit into `/root/src/repos` (`swcstudiospace/repos`). Do not push.
- **Runtime**: One Python process. No Node or Rust agent process beside Omes. No new global toolchain.
- **Sources**: Do not vendor, subtree, or runtime-import `hermes-agent/` or `oh-my-pi/`.
- **Verification**: A completion claim needs a command and an exit code (programming-desk PD-1). No secrets (PD-4). No destructive operation without recorded approval (PD-5).
- **Providers**: A missing xAI key does not fail the milestone. The Grok adapter is tested with a fake transport.
- **Done means parity**: A phase is done when its parity checks pass, not when a scaffold exists.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| One Python process, one OmesAgent | The user wants both agents' logic merged into one bot, not a router in front of two checkouts | — Pending |
| Hermes is move-and-adapt; Omp is a behavior port into that same agent | The loop already exists in Python. Omp's TypeScript tests are the spec for harness behavior | — Pending |
| Temporal is deferred | It was a candidate because the languages differ. It is not required to call the port done | — Pending |
| Milestone discuss is the approved plan | Re-asking the merge would stall a decision that is already made | ✓ Good |
| Product chrome stays out unless a phase's own tests cannot pass without it | The milestone is the agent, not the apps wrapped around it | — Pending |
| Grok shell stays in step with the registry | The roster is the index of tools actually registered. The template lists only skills and routines that exist on disk | — Pending |

---
*Last updated: 2026-10-02 after Phase 0 repo boundary*
