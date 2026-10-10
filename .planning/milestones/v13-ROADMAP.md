# Roadmap: Omega Prime

## v13 Grok Bot specialisation — shipped 2026-10-09

**Status:** Complete. 3/3 phases, 10/10 requirements. Audit passed.

Grok Bot has the tools and the Python loop, and no interaction layer that tells it when to call them. This milestone adds that layer: `/omega-*` slash commands, workflows that run those tools in order, routines the template can name, one seeded memory, and an onboarding pass that asks for missing connector env names without taking secrets in chat.

- [x] **Phase 68: Slash commands and workflows** — Command parser, catalog, workflow runner, seed memory, connector requests. (GBX-01, GBX-03, GBX-05, GBX-06, GBX-07)
- [x] **Phase 69: Grok surface** — `omega_command` on the served roster, template, prompt, skill, routines, and the Python agent intercept. (GBX-02, GBX-04, GBX-08)
- [x] **Phase 70: Milestone audit + closeout** — Audit, archive, full gates. (DONE-01, DONE-02)

### Phase 68: Slash commands and workflows

**Goal:** A message that is only `/omega-<name>` runs a catalog command or a fixed workflow. Secrets are refused. One checked-in memory is seeded.
**Requirements:** GBX-01, GBX-03, GBX-05, GBX-06, GBX-07
**Success criteria:**

  1. `parse_omega_command` accepts a whole `/omega-...` message and rejects prose.
  2. The twelve-name catalog runs through the registry. Unknown names and missing args are errors.
  3. `python-clean` stops on a non-zero exit. `onboard` and `desk` record an error and continue.
  4. `onboard` seeds `grokbot/seeds/memory.txt` through `memory`, tagged `[hindsight:omega-prime-lead]`.
  5. `/omega-connectors` lists requests and never copies a set token into the result.

### Phase 69: Grok surface

**Goal:** Grok Bot can see and call the slash commands. First run is `/omega-onboard`. A pure slash message does not call the model.
**Requirements:** GBX-02, GBX-04, GBX-08
**Success criteria:**

  1. `omega_command` is served beside `delegate_task`. The default host serves 110 tools.
  2. Routines `onboard`, `python-clean`, and `connectors` are named by the template and the seat prompt.
  3. `OmegaPrimeAgent.run` dispatches a pure `/omega-...` message and does not call the model.
  4. Desk bootstrap no longer tells this bot to start with `/desk bootstrap`.

### Phase 70: Milestone audit + closeout

**Goal:** Every requirement has command evidence, the phase directories are archived, and the final tree is green.
**Requirements:** DONE-01, DONE-02
**Success criteria:**

  1. `.planning/v13-MILESTONE-AUDIT.md` status is `passed`.
  2. Phase directories live under `milestones/v13-phases/`.
  3. pytest, mypy, ruff, evals, assemble, catalog, and setup_check pass on the final tree.

## Decisions

- One served tool, `omega_command`, is how Grok invokes a slash command. The Python agent uses the same dispatcher when the whole user message is `/omega-...`.
- Workflows are fixed step lists. They dispatch registry tools. They do not invent success.
- Connector onboarding reports missing env names. It never reads a secret into the reply.
- `/omega-python` is ruff and compileall. Full suites stay on `/omega-gates`.
- Prime families stay off by default.

## Known limits

No live Grok account, live model, or live connector. SEED-010's MCP prompts and resources remain unbuilt. Nyquist and security phase artifacts were not generated.
