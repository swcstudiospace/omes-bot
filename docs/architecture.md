# Architecture

How Omes Bot is put together: one process, one loop, one registry, and the
planes around them. Counts below are exact at release time (109 tools,
26 skills, 4 routines, 310 tests, 23 evals).

## The shape

```text
prompt ──▶ loop ──▶ registry ──▶ tools ──▶ receipts
             │          │
          skills     policy + broker + journal
             │          │
        memory ◀── substrate surface ──▶ Hindsight / RAGflow
```

Everything runs in one Python process (`omes/`). There is no sidecar, no
Node agent process, no Rust service beside it.

## The loop

`omes/agent/conversation_loop.py` runs one turn: install the system prompt
once, take the user row, then iterate model call → tool round or text reply
until something finishes the turn. The Omp harness rides the same loop as
options on the `Agent` (pause gates, output budgets, plan mode, extensions).
Magic keywords (`ultrathink`, `orchestrate`, `workflowz`) inject notices for
the turn when they appear as standalone prose.

## The registry

`omes/tools/registry.py` maps 109 tool names to handlers across 17 families
(coding, growth, platform, IDE, connectors, seven desk packs, app packs,
ultrathink, substrate). Dispatch always returns JSON; unknown names are
errors, never exceptions. Three gates wrap every call, in order: the seat
policy (allowed tools/hosts/paths), the approval log (mutating tools wait
for a person), and the audit + tracer (one verdict and span per dispatch).

The roster is the contract: `omes/contracts/tool-rosters/omes.yaml` must
list exactly the registered names, and the policy must allow every one.
The suite enforces both, and the [tool catalog](tool-catalog.md) is
generated from the live registry so docs cannot drift.

## Memory and skills

Two file-backed stores (`MEMORY.md`, `USER.md`) plus bank-tagged episodic
recall serve every call shape: Hermes learn/recall, Omp mnemopi, and the
Hindsight `retain`/`recall` pair. Skills are `SKILL.md` files under
`omes/skills/` (26); routines are prompt flows (`sweep`, `nightly`,
`ultrathink_turn`) plus the desk lead routines. The curator folds nightly
learnings back into memory.

## The Grok Bot shell

The same agent, addressed from Grok: `omes/grokbot/templates/OMES.md` is
the Add-Bot template (name, description, empty skill/routine sections —
bodies live in the repo), `grokbot/SETUP.md` is the four-step install, and
`omes/scripts/assemble-prompts.sh` builds `prompts-assembled/OMES.xml`
from the seat XML plus shared directives. `--check` fails CI on drift.

## The substrate surface

On wired installs the turn opens with a shared brief from substrate-mcp
and reports session/prompt/tool/file events with graph provenance; memory
writes go through the shared plane; episodes come from the shared
`ultrathink` Hindsight bank with local fallback; docs answer from RAGflow.
See [Substrate surface](substrate.md). GreptimeDB, TimescaleDB, and
DragonflyDB stay behind the store lock — Omes holds no clients for them,
and a test fails the build if one appears.

## Verification

| Gate | Command | Current |
| --- | --- | --- |
| Suite | `pytest omes/tests -q` | 310 passed |
| Evals | `omes.evals.runner omes/evals/cases` | 23 passed |
| Assembly | `assemble-prompts.sh --check` | clean |
| Setup | `omes.setup_check --root .` | clean |
| Docs | catalog `--check` + link tests | clean |

A completion claim without a command and an exit code is not a claim.
See [Verification receipts](user-guide.md) and CONTRIBUTING.md.
