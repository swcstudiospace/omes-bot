# Requirements: Omega Prime v13 Grok Bot specialisation

**Defined:** 2026-10-09
**Archived:** 2026-10-09
**Outcome:** All 10 requirements validated. No requirements dropped or adjusted. Audit passed (`.planning/v13-MILESTONE-AUDIT.md`).

**Core Value:** Grok Bot can run Omega Prime on purpose. A slash command, a workflow, a routine, a seeded memory, and a connector request are real call paths, not files the model has to guess about.

v12 remains archived in `milestones/v12-REQUIREMENTS.md`. No v12 requirement was reopened.

## v13 Requirements

### Slash commands and workflows (Phase 68)

- [x] **GBX-01**: A user message that is only `/omega-<name>` is a slash command. `parse_omega_command` accepts that shape and rejects prose that merely mentions one. `execute_command` runs the catalog (`omega-help`, `omega-doctor`, `omega-roster`, `omega-recall`, `omega-retain`, `omega-gates`, `omega-python`, `omega-delegate`, `omega-workflow`, `omega-onboard`, `omega-connectors`, `omega-desk`). Unknown names and missing args are errors. A retain that looks like a secret is refused before any tool call.
- [x] **GBX-03**: Named workflows `onboard`, `python-clean`, `connectors`, and `desk` run a fixed step list through the registry. `python-clean` is `ruff check` then `compileall` via `run_terminal` argv, and it stops on a non-zero exit. `onboard` and `desk` record a step error and still run the later steps. No step fabricates success.
- [x] **GBX-05**: `onboard` seeds one checked-in memory entry, tagged `[hindsight:omega-prime-lead]`, by calling the `memory` tool. The seed names the slash commands and says tokens are not pasted into chat. The seed file contains no secret and no `§`.
- [x] **GBX-06**: `/omega-connectors` lists configured connector ids and a request for each missing one (env names plus a one-line ask). A set token is never copied into the result. Blank env values count as missing.
- [x] **GBX-07**: `/omega-python` is the short Python check (ruff and compileall). `/omega-gates` dispatches `qua_gates_run` and does not pretend the suites passed.

### Grok surface (Phase 69)

- [x] **GBX-02**: `omega_command` is on the served roster, registered beside `delegate_task`, and accepts the slash text. The tool description tells the model when to use it.
- [x] **GBX-04**: Routines `onboard`, `python-clean`, and `connectors` are files under `routines/`, named by the Grok template and by the seat prompt.
- [x] **GBX-08**: The template, the seat prompt, and `skills/omega-commands/SKILL.md` say when Grok calls `omega_command`. First run is `/omega-onboard`. The desk-bootstrap adaptation no longer sends this bot through `/desk bootstrap` as its first run. `OmegaPrimeAgent.run` executes a pure `/omega-...` message through `omega_command` and does not call the model. Prose still goes to the model.

### Closeout (Phase 70)

- [x] **DONE-01**: Per-requirement audit with the command evidence from phases 68 and 69.
- [x] **DONE-02**: Phase directories archived, roadmap collapsed, full gates green on the final tree.

## Traceability

| ID | Phase | Outcome |
|---|---|---|
| GBX-01 | 68 | validated |
| GBX-03 | 68 | validated |
| GBX-05 | 68 | validated |
| GBX-06 | 68 | validated |
| GBX-07 | 68 | validated |
| GBX-02 | 69 | validated |
| GBX-04 | 69 | validated |
| GBX-08 | 69 | validated |
| DONE-01 | 70 | validated |
| DONE-02 | 70 | validated |

## Out of scope

- A live Grok Bot account, a live model call, or a live connector call. Missing credentials stay requests.
- Replacing Grok's hosted routine scheduler. These routines are the files and the slash commands that invoke them.
- Turning on Prime families by default.
