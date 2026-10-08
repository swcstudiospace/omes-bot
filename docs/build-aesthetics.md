# Build aesthetics

How Omes Bot is put together, and the rules every part follows.

## One process

Omes is a single Python agent: the Hermes conversation loop
(interrupt, budget, one model call, tool round or text, finalize)
fused with the oh-my-pi harness (modes, skills, memory,
delegation, scheduler). Upstream checkouts are read-only sources;
the bot lives under `omes/`.

## Packs, not seats

The seven Programming Desk seats were absorbed as domain packs —
tool families with roster entries, policy entries, and skills —
inside the one agent: lead (16), systems (6), web (6), mobile
(13), infra (7), quality (8), app packs (9). Messaging, IDE,
platform, growth, coding, delegation, substrate, and ultrathink
bridge tools complete the 109-tool roster.

## Contracts over code

Three files decide what the bot may do, and tests enforce that
the code matches exactly:

- `contracts/tool-rosters/omes.yaml` lists every offered tool, in
  registry order. Composition tests fail on any drift.
- `contracts/policies/omes.json` is the allowlist plus
  read-only paths and the (empty) network list.
- `ownership.yaml` maps every path pattern to the single owner.

Prompts assemble the same way: seat XML plus shared directives
build `prompts-assembled/OMES.xml`, and `--check` fails on drift.

## Seams, fakes, receipts

Every external thing — models, transports, CLIs, runners,
stores — arrives through an injected seam. Tests use fakes only;
no test touches the network or a live CLI (the receipts E2E runs
hermetic local commands). A completion claim cites a command and
its exit code; the quality pack refuses self-approval at both
the receipt and the stamp.

## Deterministic guards

- Hermetic pytest coverage for roster/policy/composition agreement,
  provider protocols, retrieval safety, and per-pack behavior.
- Deterministic golden and red-team evals, including refusal and approved
  behavior through real tool registration.
- CI reports the current test/eval totals; prose does not pin changing counts.
- `assemble-prompts.sh --check` and `omes.setup_check` verify
  prompts, template, roster, registry, and install health.

## Layout

| Path | Holds |
| --- | --- |
| `omes/agent/` | Loop, modes, skills runtime, delegation |
| `omes/tools/` | Registry + tool families |
| `omes/skills/` | 26 skills |
| `omes/routines/` | 5 routines |
| `omes/prompts/` | Seat + shared prompt sources |
| `omes/contracts/` | Roster, policy, pack contracts |
| `omes/grokbot/` | Template, roster JSON, setup flow |
| `omes/evals/` | Runner + golden/redteam cases |
| `omes/hosting/` | OpenShell profile, AgentOS notes |
| `docs/` | This site (GitBook-synced) |
