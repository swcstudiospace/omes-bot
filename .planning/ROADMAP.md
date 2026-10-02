# Roadmap: Omes Bot

## Overview

Omes Bot starts as an empty git root beside two ignored upstream checkouts, then grows one Python agent. The first phase is the single-seat Grok shell. The next phases port the Hermes loop, tools, skills, memory, delegation, and cron, then fold Omp's harness, edit pipeline, language servers, modes, and memory into that same agent. The last phase is the provider surface and a Grok Bot template that names only what the agent actually registers. A phase is done when its parity checks pass.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Single-seat shell** - One bot prompt, roster, template, and a deterministic assembler.
- [ ] **Phase 2: Hermes loop** - Conversation loop, turn phases, and the prompt, steer, compression, and interrupt invariants.
- [ ] **Phase 3: Coding toolset** - Registry, discovery, and the file, search, terminal, todo, clarify, web, and vision tools.
- [ ] **Phase 4: Skills and memory** - Skill manager, memory provider, session search, and the curator.
- [ ] **Phase 5: Delegation and cron** - Isolated children and a scheduler that re-enters the same agent.
- [ ] **Phase 6: Remaining Hermes tools** - Code execution, MCP, browser, approvals, and plugin tool registration.
- [ ] **Phase 7: Omp harness** - Events, steering, pause, budget, and compaction merged into the phase 2 loop.
- [ ] **Phase 8: Edit pipeline** - Apply, reject a bad hunk, and repair.
- [ ] **Phase 9: LSP and DAP** - A fixture diagnostic and a breakpoint session.
- [ ] **Phase 10: Modes and learning** - Sessions, tasks, plan mode, extensions, autolearn, goals, advisor, exec, and security checks.
- [ ] **Phase 11: Memory unification** - Omp memories, hindsight, and mnemopi on the phase 4 store.
- [ ] **Phase 12: Providers and install surface** - Provider contract, Grok adapter, remaining adapters, and a template that matches the registry.

## Phase Details

### Phase 1: Single-seat shell
**Goal**: A person can read one bot prompt that points at skills, the tool roster, and the prompt folder, assemble it twice and get the same bytes, and open a Grok Bot template that names nothing that is not on disk.
**Depends on**: Nothing (first phase)
**Requirements**: SHELL-01, SHELL-02, SHELL-03, SHELL-04
**Success Criteria** (what must be TRUE):
  1. The seat prompt parses, and assembling it twice writes identical bytes.
  2. The assembled prompt points at the skills directory, the tool roster, and the prompt sources.
  3. Every skill and routine named in the template exists on disk. An empty list is valid while none exist.
  4. The core directives require a command and exit code before a completion claim, forbid committing a secret, and require recorded approval before a destructive operation.
**Plans**: 1 plan

Plans:
- [x] 01-01: Single-seat prompt, roster, template, and assembler

### Phase 2: Hermes loop
**Goal**: One conversation loop runs a tool round and a text finish, and keeps the Hermes invariants while it does.
**Depends on**: Phase 1
**Requirements**: LOOP-01, LOOP-02, LOOP-03, LOOP-04, LOOP-05
**Success Criteria** (what must be TRUE):
  1. A tool round leaves the system prompt byte-for-byte unchanged.
  2. A steer is stored as its own user message after the tool result.
  3. Prior context changes only when compression runs.
  4. An interrupt stops the loop before another model call.
**Plans**: 1 plan

Plans:
- [ ] 02-01: Move and adapt the Hermes conversation loop and turn phases

### Phase 3: Coding toolset
**Goal**: The agent can call the coding tools by name, and it is not offered a tool the roster does not list.
**Depends on**: Phase 2
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04
**Success Criteria** (what must be TRUE):
  1. File, patch, search, local terminal, todo, clarify, web, and vision each run through the registry.
  2. A name that is not registered does not run.
  3. A tool that is registered but absent from the roster is not included in the tool list sent to the model.
**Plans**: 1 plan

Plans:
- [ ] 03-01: Registry, discovery, and the coding toolset

### Phase 4: Skills and memory
**Goal**: The agent can write a skill it later loads, recall a memory it wrote, and search a past session. The curator only keeps a skill the turn earned.
**Depends on**: Phase 3
**Requirements**: GROW-01, GROW-02, GROW-03, GROW-04, GROW-05
**Success Criteria** (what must be TRUE):
  1. A turn writes a skill under the skills directory and a later turn loads that file by path.
  2. A memory write is returned by a recall on a later turn.
  3. Session search finds a message that was stored in the session.
  4. The curator leaves the skill tree unchanged when the turn did not earn a skill.
**Plans**: 1 plan

Plans:
- [ ] 04-01: Skill manager, memory provider, session search, and curator

### Phase 5: Delegation and cron
**Goal**: The agent can hand work to a child and run a scheduled job through the same conversation loop.
**Depends on**: Phase 4
**Requirements**: DELEG-01, DELEG-02, CRON-01
**Success Criteria** (what must be TRUE):
  1. The parent transcript gains the child summary and does not gain the child's tool messages.
  2. The parent toolset after the child returns matches the toolset from before the child started.
  3. A job that is due runs through the conversation loop and records its result.
**Plans**: 1 plan

Plans:
- [ ] 05-01: Child lifecycle and the cron scheduler

### Phase 6: Remaining Hermes tools
**Goal**: Code execution, MCP, the browser, approvals, and a plugin-registered tool all dispatch through the same registry against a temporary home.
**Depends on**: Phase 5
**Requirements**: TOOL-05, TOOL-06, TOOL-07, TOOL-08, TOOL-09, TOOL-10
**Success Criteria** (what must be TRUE):
  1. Code execution, the MCP client, and the browser toolset each run a fixture call through the registry.
  2. A tool that requires approval does not run until approval is recorded.
  3. A plugin registers a tool that then dispatches like a built-in, inside a temporary home directory.
**Plans**: 1 plan

Plans:
- [ ] 06-01: Code execution, MCP, browser, approvals, and plugin tools

### Phase 7: Omp harness
**Goal**: The phase 2 loop also behaves like the Omp agent core, still as one agent class.
**Depends on**: Phase 6
**Requirements**: HARNESS-01, HARNESS-02, HARNESS-03, HARNESS-04
**Success Criteria** (what must be TRUE):
  1. A turn emits start, message, and end events, and a before-model hook can change the outgoing request.
  2. Pause holds the loop, and a steer injected mid-turn is delivered as its own user row.
  3. A tool result marked useless is not treated as an error, and an output budget stops a runaway turn.
  4. The phase 2 prompt, steer, compression, and interrupt checks still pass.
**Plans**: 1 plan

Plans:
- [ ] 07-01: Merge the Omp agent-core behavior into the conversation loop

### Phase 8: Edit pipeline
**Goal**: The agent can apply an edit, refuse a bad hunk without touching the file, and repair a hunk that did not land.
**Depends on**: Phase 7
**Requirements**: EDIT-01, EDIT-02, EDIT-03
**Success Criteria** (what must be TRUE):
  1. A well-formed edit changes the fixture file as specified.
  2. A bad hunk leaves the file byte-for-byte unchanged.
  3. A repair pass applies a hunk the first attempt could not place.
**Plans**: 1 plan

Plans:
- [ ] 08-01: Port the Omp edit pipeline

### Phase 9: LSP and DAP
**Goal**: The agent can ask a language server about a fixture project and can stop a fixture program on a breakpoint.
**Depends on**: Phase 8
**Requirements**: IDE-01, IDE-02
**Success Criteria** (what must be TRUE):
  1. An LSP session on a fixture project returns at least one diagnostic for a known error.
  2. A DAP session stops on a breakpoint and reports that stop.
**Plans**: 1 plan

Plans:
- [ ] 09-01: LSP diagnostics and a DAP breakpoint session

### Phase 10: Modes and learning
**Goal**: The agent can resume a session, refuse writes while planning, run an extension hook before the model, and record a learned skill through the skill manager.
**Depends on**: Phase 9
**Requirements**: MODE-01, MODE-02, MODE-03, MODE-04, MODE-05
**Success Criteria** (what must be TRUE):
  1. A saved session and a saved task can be loaded on a later run.
  2. Plan mode rejects a write tool call and leaves the file unchanged.
  3. An extension hook runs before the model call and can be observed from the test.
  4. Autolearn writes through the phase 4 skill manager, and goals, advisor, exec job control, and the agent security check each run once in a fixture.
**Plans**: 1 plan

Plans:
- [ ] 10-01: Sessions, tasks, modes, extensions, autolearn, and agent controls

### Phase 11: Memory unification
**Goal**: Hermes memory calls and Omp memory calls read and write one store.
**Depends on**: Phase 10
**Requirements**: MEM-01, MEM-02
**Success Criteria** (what must be TRUE):
  1. A value written with the Hermes memory call is read back with the Omp memory call.
  2. Hindsight and mnemopi clients persist through that same provider.
**Plans**: 1 plan

Plans:
- [ ] 11-01: Land Omp memory clients on the phase 4 provider

### Phase 12: Providers and install surface
**Goal**: A fake provider can drive the agent, the Grok adapter speaks the same contract, and the template, roster, and assembled prompt match the tools and skills that exist.
**Depends on**: Phase 11
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06
**Success Criteria** (what must be TRUE):
  1. A fake transport completes a turn through the provider contract, and the Grok adapter uses that same contract.
  2. The remaining provider adapters each answer the contract with a fake transport.
  3. The template, roster, and assembled prompt name no tool, skill, or routine that is not registered or on disk.
  4. A completion claim with no command fails the receipt check.
**Plans**: 1 plan

Plans:
- [ ] 12-01: Providers, Grok adapter, and the install-surface check

## Progress

**Execution Order:**

Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Single-seat shell | 1/1 | Complete | 2026-10-02 |
| 2. Hermes loop | 0/1 | Not started | - |
| 3. Coding toolset | 0/1 | Not started | - |
| 4. Skills and memory | 0/1 | Not started | - |
| 5. Delegation and cron | 0/1 | Not started | - |
| 6. Remaining Hermes tools | 0/1 | Not started | - |
| 7. Omp harness | 0/1 | Not started | - |
| 8. Edit pipeline | 0/1 | Not started | - |
| 9. LSP and DAP | 0/1 | Not started | - |
| 10. Modes and learning | 0/1 | Not started | - |
| 11. Memory unification | 0/1 | Not started | - |
| 12. Providers and install surface | 0/1 | Not started | - |
