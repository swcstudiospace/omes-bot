# v6 Runtime Spike: where Omes actually runs on Grok Bot

**Date:** 2026-10-03. **Question:** does Grok Bot run our code, or do we
need a runtime? Plus: how Add-Bot distribution, magic keywords,
ultrathink integration, and GitBook fit.

## Findings

### 1. Grok Bot runs on xAI's cloud computer, not ours

Grok Bot (xAI agent product, beta Aug 2026): every bot on an account
shares one cloud computer; bots work with the laptop closed. A shared
bot installs via **Add to Grok Bot** (x.ai preview + Grok Bot app),
which creates an independent **copy** on the recipient's account.

What a template carries: instructions, skills, routines,
first-party plugins. What it does **not** carry: secrets, custom MCP
servers, scripts, personal/private skills. No self-serve plugin/skill
marketplace (listings are staff-added); distribution is Share-as-template.

**Answer:** Grok Bot does not use `~/src/repos/claude-ultrathink`,
does not run on the Cursor VM / AgentOS machine, and does not execute
the Omes Python tools. It runs Grok's default model on xAI's computer
with whatever the template + installer-configured connectors provide.

### 2. OpenShell and AgentOS are real, and both fit as our tool host

- **NVIDIA OpenShell** (Apache 2.0, v0.1.0, Sept 2026): sandboxed
  agent runtime with kernel-level isolation + policy enforcement.
  Nominally supports Hermes agents already; Omes embeds the Hermes
  loop. Installs on Linux/Mac/WSL2.
- **Rivet AgentOS** (preview): per-agent lightweight VM actor
  (Wasm/V8) with `@rivet-dev/agentos-pi` Pi-agent support; Omes
  embeds Omp behavior.

Both are places to run an **Omes tool host** (MCP server over the
Omes registry) that a Grok Bot install connects to as custom MCP —
a per-installer setup step, since custom MCP does not transfer via
template.

### 3. Omes has no MCP server side today

Omes has MCP *client* tools (`mcp_call`, `mcp_session`) only. The
desk pattern (gateway serving `/mcp/<seat>`) was never ported as a
server. An Add-Bot with real Omes tools needs `omes` servable over
MCP (stdio or HTTP) + an OpenShell/AgentOS host profile.

### 4. Magic keywords port is concrete

Omp source: `packages/coding-agent/src/modes/magic-keywords.ts`
(single table) + `prompts/system/{ultrathink,orchestrate,workflow}-notice.md`
(3/40/111 lines). Matching rules are precise (lowercase standalone
prose; code spans/blocks ignored; per-turn; requires gates:
orchestrate needs `task`, workflowz needs `task`+`eval`).

Port shape: a Python matcher + three notices adapted to Omes tools
(`task`→`delegate_task`, `edit/write`→file tools,
`bash`→`run_terminal`, `todo`→`todo_write`), injected in the Omes
conversation loop. `workflowz`'s eval-kernel contract has no Omes
equivalent and must be rewritten against `delegate_task`/routines.

### 5. Ultrathink integration has three levels (and a license catch)

claude-ultrathink is TypeScript/Bun, **AGPL-3.0**. Omes-Bot has **no
LICENSE file**. Options:

- L1 prompt-native: port the Grok-host block
  (`hosts/grok/ultrathink.md`) + plan/kickoff/ship routines into
  Omes skills/routines. No dependency, no license contagion.
- L2 bridge: Omes tools shelling to the `bun` ultrathink CLI
  (uplift/track/ship). Separate process; AGPL contained.
- L3 vendor/port: copy or translate TS sources into Omes. AGPL
  would cover the port; requires licensing Omes-Bot AGPL (or
  permission from SWC Studio, same org — still a deliberate call).

Ultrathink already ships a Grok host, so L1 is mostly assembling
existing pieces.

### 6. GitBook = Git Sync docs-as-code

GitBook Git Sync publishes `docs/` from the GitHub repo. Deliverable
is repo content (`docs/`, `SUMMARY.md`, config); connecting sync is
a user dashboard action on swcstudiospace/omes-bot (same class as
the Greptile connection already pending).

## Recommendation

- **Ship the Add-Bot as a template product:** polished OMES
  template + share link + setup flow (install → secrets → optional
  custom MCP → smoke prompt). No Grok UI is buildable; the template
  + docs + setup routine are the product surface.
- **Build the tool host:** Omes MCP server (stdio first) +
  OpenShell profile + AgentOS notes, so installs can attach real
  Omes tools. Default install works without it (prompt/skills only).
- **Magic keywords:** full port of the three words into the Omes loop.
- **Ultrathink:** L1 prompt-native + L2 bridge tools; no vendoring.
- **License:** add MIT LICENSE to Omes-Bot (keeps L1/L2 clean;
  revisit if L3 is ever wanted).
- **Docs:** `docs/` (aesthetics, user guide, setup flow) structured
  for GitBook Git Sync.
