# FAQ

Short answers, grounded in the repo. Anything here that stops matching the
code is a bug — file it.

## Install and run

**What do I need installed?**
Python 3.11+ and git. `pip install -e .` inside a venv, then the four
gates in CONTRIBUTING.md. No Node, Rust, or Docker.

**The setup check skips ultrathink/substrate. Is that a failure?**
No. Skips mean "unwired" — those planes stay local until you configure
them. Only `FAIL` fails.

**Where do secrets go?**
The host environment, never chat, never files. The credential broker
resolves them per approved host and redacts them from transcripts,
events, and errors. See SECURITY.md.

## The agent

**Skills vs routines — what's the difference?**
Skills are `SKILL.md` prompt files the agent reads when relevant.
Routines are flows the agent runs: engagement sweeps, nightly learning,
ultrathink turns. The template lists neither by body — both live on disk.

**Why did my tool call need approval?**
Mutating and shared-state tools (publishing, graph claims, memory writes
to shared scopes) wait for a person. Reads and local writes run free.
Approvals live in the approval log, enforced at dispatch.

**What are receipts?**
Proof attached to claims: the command, its exit code, and what it changed.
A completion claim without one is not a claim. Pack approvals and waivers
write receipt files under `.receipts/`.

## Grok Bot specifics

**What transfers when I Add-Bot the template?**
Name, description, and pointers. No secrets, no prompt body, no MCP
servers — those stay in the repo or on your host. See `grokbot/SETUP.md`.

**Why does the bot say a tool isn't available?**
The roster is the truth: the bot claims only tools in
`contracts/tool-rosters/omega-prime.yaml`. Anything else is a gap — file it.

## Substrate and memory

**Do I need the substrate running?**
No. Unwired installs run fully local: briefs are empty, events go
nowhere, memory stays in files. Wire it when you want cross-agent briefs,
shared memory, Hindsight episodes, and RAGflow docs.

**Local memory vs Hindsight vs substrate memory?**
Local files are the offline base. Hindsight episodes (shared `ultrathink`
bank) are recallable experience with local fallback. Substrate memory is
the cross-agent plane with accepted/quarantined/denied verdicts.

## Docs and reviews

**How do docs stay current?**
Generated pages (tool catalog) are rebuilt by script and CI fails on
drift. Every page is link-checked by the suite. Greptile reviews each PR
against the repo's review standards in `.greptile/`.
