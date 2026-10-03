# Milestone v1 archive — REQUIREMENTS (all Done, 2026-10-03)

# Requirements: Omes Bot

**Defined:** 2026-10-02
**Core Value:** One Omes agent runs both Hermes and Omp agent logic.

## v1 Requirements

Requirements for the first milestone. Each maps to one roadmap phase.

### Shell

- [x] **SHELL-01**: One seat prompt points at the skills folder, the tool roster, and the prompt folder.
- [x] **SHELL-02**: Assembling that prompt is deterministic.
- [x] **SHELL-03**: The Grok Bot template lists only skills and routines that exist on disk.
- [x] **SHELL-04**: Core directives require a receipt for a completion claim, forbid committing secrets, and require recorded approval before a destructive operation.

### Loop

- [x] **LOOP-01**: The conversation loop runs the Hermes turn phases, including session lease, budget, interrupt, prompt builder, and compression.
- [x] **LOOP-02**: The system prompt stays byte-stable across a tool round.
- [x] **LOOP-03**: A steer is its own user row after a tool result.
- [x] **LOOP-04**: Compression is the only rewrite of prior context.
- [x] **LOOP-05**: An interrupt stops the loop.

### Coding tools

- [x] **TOOL-01**: Tools register and are discovered through one registry.
- [x] **TOOL-02**: File, patch, search, local terminal, todo, clarify, web search and extract, and vision dispatch through that registry.
- [x] **TOOL-03**: A call by name runs the registered tool.
- [x] **TOOL-04**: A tool absent from the roster is not offered to the model.

### Growth

- [x] **GROW-01**: Skill create and update write under the skills directory, with the Hermes guards.
- [x] **GROW-02**: A turn can write a skill that the next turn loads by path.
- [x] **GROW-03**: A memory write is recalled on a later turn.
- [x] **GROW-04**: Session search returns from the session store.
- [x] **GROW-05**: The curator does not invent a skill the turn did not earn.

### Delegation and cron

- [x] **DELEG-01**: A child is isolated, restores the parent toolset, and respects depth, concurrency, background completion, and leaf versus orchestrator.
- [x] **DELEG-02**: The parent sees the child summary, not the child's tool traffic.
- [x] **CRON-01**: A due job runs through the same conversation loop.

### Remaining Hermes tools

- [x] **TOOL-05**: Code execution dispatches through the registry.
- [x] **TOOL-06**: The MCP client dispatches through the registry.
- [x] **TOOL-07**: The browser toolset dispatches through the registry.
- [x] **TOOL-08**: Approvals gate a tool that declares it needs approval.
- [x] **TOOL-09**: A plugin can register a tool on the same registry.
- [x] **TOOL-10**: Each of those toolsets runs against a temporary home.

### Harness

- [x] **HARNESS-01**: The loop emits the Omp agent events and runs before-model, pause, and live-steering hooks.
- [x] **HARNESS-02**: Output budget and useless-versus-error tool results match the Omp behavior.
- [x] **HARNESS-03**: Speculative execution and the extra compaction rules from Omp run inside the same loop.
- [x] **HARNESS-04**: The phase 2 invariants still hold. There is one agent class.

### Edit pipeline

- [x] **EDIT-01**: An edit applies to a fixture file.
- [x] **EDIT-02**: A bad hunk is rejected and the file is unchanged.
- [x] **EDIT-03**: A repair pass fixes a hunk the first apply could not place.

### Language and debug servers

- [x] **IDE-01**: An LSP session returns a diagnostic on a fixture project.
- [x] **IDE-02**: A DAP session hits a breakpoint in a fixture program.

### Modes and learning

- [x] **MODE-01**: Sessions and tasks persist and resume.
- [x] **MODE-02**: Plan mode cannot call a write tool.
- [x] **MODE-03**: An extension hook runs before the model call.
- [x] **MODE-04**: Autolearn records through the phase 4 skill manager.
- [x] **MODE-05**: Goals, advisor, exec job control, and agent-side security checks run in the agent.

### Memory unification

- [x] **MEM-01**: Omp memories, the hindsight client, and mnemopi use the phase 4 memory provider.
- [x] **MEM-02**: One store serves both the Hermes and the Omp call shapes.

### Providers and install surface

- [x] **PROV-01**: A provider contract accepts a fake transport and returns a model response.
- [x] **PROV-02**: The Grok adapter speaks that contract. Tests use a fake transport.
- [x] **PROV-03**: The remaining `packages/ai` adapters are ported as tasks in this phase.
- [x] **PROV-04**: The template, the roster, and the assembled prompt name only tools, skills, and routines that exist.
- [x] **PROV-05**: A completion claim with no command fails the receipt check.
- [x] **PROV-06**: The roster contains no tool name the registry does not export.

## v2 Requirements

Deferred. Not in this roadmap.

### Durability

- **DUR-01**: A Temporal worker can resume cron and delegation after a process restart.

### Chrome

- **CHROME-01**: A terminal UI on the same agent.
- **CHROME-02**: A messaging gateway on the same agent.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Temporal as the merge mechanism | One Python process is the merge. Temporal is a later adapter. |
| Sidecar that shells out to the two checkouts | Both agents are ported into Omes. |
| Hermes TUI, desktop, website, locales, nix and docker packaging | Product chrome around the agent. |
| Messaging gateways, Feishu, Yuanbao, Home Assistant, Spotify, kanban UI | Product chrome. Pulled in only if a phase's tests cannot pass without that code. |
| Omp TUI, collab web, stats site, CLI gallery, Rust crates, bazel and nix | Product chrome and the non-Python core. The agent loop is the port. |
| Push or a new GitHub repository | Not authorized for this milestone. |
| Provisioning a Grok Bot account | The template file is the install surface. |
| Seven-seat desk channel rules | This bot is one seat. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHELL-01 | Phase 1 | Done |
| SHELL-02 | Phase 1 | Done |
| SHELL-03 | Phase 1 | Done |
| SHELL-04 | Phase 1 | Done |
| LOOP-01 | Phase 2 | Done |
| LOOP-02 | Phase 2 | Done |
| LOOP-03 | Phase 2 | Done |
| LOOP-04 | Phase 2 | Done |
| LOOP-05 | Phase 2 | Done |
| TOOL-01 | Phase 3 | Done |
| TOOL-02 | Phase 3 | Done |
| TOOL-03 | Phase 3 | Done |
| TOOL-04 | Phase 3 | Done |
| GROW-01 | Phase 4 | Done |
| GROW-02 | Phase 4 | Done |
| GROW-03 | Phase 4 | Done |
| GROW-04 | Phase 4 | Done |
| GROW-05 | Phase 4 | Done |
| DELEG-01 | Phase 5 | Done |
| DELEG-02 | Phase 5 | Done |
| CRON-01 | Phase 5 | Done |
| TOOL-05 | Phase 6 | Done |
| TOOL-06 | Phase 6 | Done |
| TOOL-07 | Phase 6 | Done |
| TOOL-08 | Phase 6 | Done |
| TOOL-09 | Phase 6 | Done |
| TOOL-10 | Phase 6 | Done |
| HARNESS-01 | Phase 7 | Done |
| HARNESS-02 | Phase 7 | Done |
| HARNESS-03 | Phase 7 | Done |
| HARNESS-04 | Phase 7 | Done |
| EDIT-01 | Phase 8 | Done |
| EDIT-02 | Phase 8 | Done |
| EDIT-03 | Phase 8 | Done |
| IDE-01 | Phase 9 | Done |
| IDE-02 | Phase 9 | Done |
| MODE-01 | Phase 10 | Done |
| MODE-02 | Phase 10 | Done |
| MODE-03 | Phase 10 | Done |
| MODE-04 | Phase 10 | Done |
| MODE-05 | Phase 10 | Done |
| MEM-01 | Phase 11 | Done |
| MEM-02 | Phase 11 | Done |
| PROV-01 | Phase 12 | Done |
| PROV-02 | Phase 12 | Done |
| PROV-03 | Phase 12 | Done |
| PROV-04 | Phase 12 | Done |
| PROV-05 | Phase 12 | Done |
| PROV-06 | Phase 12 | Done |

**Coverage:**

- v1 requirements: 49 total
- Mapped to phases: 49
- Unmapped: 0

---
*Requirements defined: 2026-10-02*
*Last updated: 2026-10-03 after milestone audit (all 49 requirements Done)*
