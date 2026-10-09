---
phase: 61-prime-loop-gap-closure
plan: "05"
subsystem: prompt-roster-catalog
tags: [default-off, effective-roster, assembled-prompt, tool-catalog, approval-metadata]
status: product_verified_review_repaired
requires:
  - phase: 57
    provides: Per-family config flags (default off), prime_enabled and config.PRIME_FAMILIES
  - phase: 61-03
    provides: Unchanged family tool-name membership; typed schemas the catalog reads
provides:
  - Assembled seat prompt that omits the tool entries of disabled Prime families and offers an enabled family without leaking others
  - Canonical default-off assembly that reads no user config, HOME or process environment
  - Tool catalog whose approval and required-parameter metadata come from the actual family registrations
affects: [61-06, v10-closeout]
tech-stack:
  added: []
  patterns: [render() additive config parameter, family TOOL_NAMES constants, real registration inventory without dispatch]
key-files:
  modified:
    - omega_prime/assemble.py
    - omega_prime/tooling/catalog.py
    - omega_prime/tests/test_shell.py
    - omega_prime/prompts-assembled/OMEGA_PRIME.xml
    - docs/tool-catalog.md
key-decisions:
  - "Filter at render time from each family's own TOOL_NAMES constant; the template stays the allowed superset and no 'use only live tools' prose was added."
  - "render(root, roster) keeps its two-argument API; config=None is the canonical default-off assembly and reads no ambient state."
  - "The catalog registers every family's real definitions without dispatching a handler and fails closed on a rostered tool with no definition rather than inventing 'not required / none'."
requirements-completed: [LOOP-05, REPO-03]
requirements-open: []
coverage:
  - id: effective-roster-and-prompt
    description: Default-off effective offers and assembled prompt exclude all 37 Prime tools; harness-only config adds exactly the harness tools; ordinary tools remain
    requirement: LOOP-05
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_surface_smoke
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_shell.py
        status: pass
    human_judgment: false
  - id: truthful-catalog-metadata
    description: Catalog approval and required-parameter lines for all 37 Prime tools match the real registration inventory; generation and drift check succeed
    requirement: REPO-03
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_generated_checks
        status: pass
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_surface_smoke
        status: pass
    human_judgment: false
  - id: docs-structure-preserved
    description: Docs set and GitBook structure criterion, inherited receipt only (not re-run after the Plan 05/06 doc edits)
    requirement: REPO-03
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#current_source_policy_smoke
        status: pass
    human_judgment: false
completed: 2026-10-09
---

# Plan 61-05 — Config-derived effective prompt/roster and truthful catalog

`PromptCatalogRepair` executed the bounded source slice with no mid-flight checks or
commits. The parent ran the generators once after integration and every gate. This
summary is not a full32 or signed A09/A10/A11 gate. Code descriptions come from the
final tree; the later review-repair wave touched the assembler CLI again and is
described only in the 61-03 summary.

## Delivered behavior

**Prompt/roster (LOOP-05).** `omega_prime/assemble.py::render(root, roster_path,
config=None)` builds the seat prompt exactly as before, then drops only exact
`<tool name="..."/>` lines whose tool belongs to a disabled Prime family
(`filter_disabled_tools`). Disabled names come from `disabled_family_tools`, which maps
`rlm, harness, goals, heartbeat, autonomous, messaging, kernel` to each family's own
`*_TOOL_NAMES` constant, applies `config.prime_enabled`, and exits if that mapping
drifts from `config.PRIME_FAMILIES`. `config=None` is the canonical default-off
assembly and reads no user config, HOME or process environment; an embedding caller
passes `load_config(...)` or an explicit dict. The CLI gained a repeatable
`--enable-family` flag for verification without mutating global config. Ordinary
instructions and tools are untouched; the committed template
(`prompts/bot-00-omega-prime.xml`) is deliberately unchanged and remains the allowed
superset, so the filtering is observable only in the assembled output. The static bot
roster `grokbot/rosters/default.json` carries no tool list (family enablement lives in
config) and is distinct from Plan 04's child-session roster records; it was not
changed. The policy contract (`contracts/tool-rosters/omega-prime.yaml`) remains an
allowlist superset by design, so "absent from roster" is satisfied for the effective
offered roster (live registry / MCP / model offers) and the assembled prompt, not for
that allowlist file.

**Catalog (REPO-03 catalog part, WARN-03).** `omega_prime/tooling/catalog.py` gained
`full_inventory_registry(root, home)`: the default registry plus real
`register_*` calls for harness, goals, heartbeat and autonomous (enabled, against the
real root), messaging on a throwaway in-memory `SessionRegistry`, RLM and
`delegate_task` with unbound `None` parents, and the kernel tools. No handler is
dispatched during generation. `render` reads `registry.approval_required(name)` and the
schema's `required` list for every rostered name and exits with an error when a
rostered name has no registered definition. Prime writers now publish `Approval:
required` with their actual required parameters (for example `rlm_spawn`: prompt, name;
`goal_set`: objective; `prime_cell`: code). `delegate_task` now renders its real
description (approval remains `not required`, as registered).

## Actual verification

Observed before: `61-EVIDENCE.json#cross_phase_before` (exit 0) recorded
`disabled_rlm_spawn_in_assembled_prompt: true`; the pre-repair audit
(`61-INTEGRATION.md`, INT-04/WARN-03, source reading) recorded Prime tools published as
`Approval: not required` / `Required params: none` from the disabled default registry.

`61-EVIDENCE.json#cross_gap_actual_surface_smoke` (exit 0, 8.94 s, isolated HOME):
default live MCP/model offers 108 with identical name sets and none of the 37 Prime
tools; actual `render` default-off prompt has 109 `<tool>` entries with none of the 37
Prime tools (the receipt records 108 and 109 without explaining the one-entry
difference); a config enabling only harness adds exactly
the six `harness_*` tools to live offers (114) and to the prompt, and no other family
appears; for all 37 Prime tools the catalog section's approval and required-params
lines equal the values read from `full_inventory_registry` (24 approval-required
Prime tools recorded: `agent_message_send`, `autonomous_start/stop`,
`goal_clear/pause/resume/set`, `harness_delete/refine/rollback/upsert`,
`heartbeat_clear/set`, `prime_autonomous`, `prime_bash`, `prime_cell`,
`prime_factory_resume/run/stop`, `prime_goal`, `rlm_create_session`,
`rlm_delete_subagent`, `rlm_rename`, `rlm_spawn`); a freshly installed
`python -m omega_prime.mcp_server` over stdio initialized as `omega-prime`, offered 108
tools and `read_file` returned the canonical assembled prompt bytes. Two earlier
launcher runs of this smoke exited 1 for harness faults (a fixture missing the
`omega_prime` directory; a nonexistent console script) with no product change
(`#cross_gap_surface_smoke_initial`, `#cross_gap_surface_launcher_correction`).

Generation (`#cross_gap_generator_after`, exit 0, 5.23 s):
`.venv/bin/python -m omega_prime.assemble && .venv/bin/python -m
omega_prime.tooling.catalog --out docs/tool-catalog.md` wrote both files. The first
cold generator attempt had failed on a circular import
(`#cross_gap_cold_import_bug`, fixed under Plan 03). `#cross_gap_generated_checks`
(exit 0): `.venv/bin/python -m omega_prime.assemble --check && .venv/bin/python -m
omega_prime.tooling.catalog --check` printed `OMEGA_PRIME up to date; docs/tool-catalog.md
up to date`. Executor-expected transient failures of the disk==render drift tests until
regeneration were resolved by that regeneration.

Integrated gates (`#cross_gap_current_full_python`): 739 passed, 12 warnings, exit 0;
fresh isolated install (`#isolated_current_full_suite_after`): 726 passed, 13 skipped,
setup exit 0 (registry serves 108 roster tools; assembly up to date); static
(`#cross_gap_final_static`): Ruff 0, 271 files formatted, mypy 236 sources 0, 26 evals,
actionlint 0. New consumer regressions in `test_shell.py`:
`test_default_render_omits_every_disabled_prime_family`,
`test_enabled_family_appears_without_leaking_other_families`,
`test_default_render_ignores_process_environment_flags`,
`test_explicit_config_enables_only_its_family`; the executor removed no pins and
repinned none.

## Parent corrections and limitations

Parent regenerated `prompts-assembled/OMEGA_PRIME.xml` and `docs/tool-catalog.md` once
after integration; neither is hand-edited. `omega_prime/tests/test_providers.py` was not
changed by this plan. REPO-03's docs-structure criterion rests on the earlier
`#current_source_policy_smoke` receipt (exit 0, `gitbook_structure_resolves: true`),
which was not re-run after this phase's later docs edits; the current `docs/SUMMARY.md`
also links ADR 0002, which that receipt does not cover. The catalog and prompt describe
registrations and offers, not native child delivery; RLM and messaging remain
live-context families that the default registry does not compose (catalog docstring; `61-INTEGRATION.md` WARN-01). No signed
A09/A10/A11 verdict, cloud CI pass or published-clone proof exists for this plan.
Literal LOOP-07, REPO-04, REPO-05, DONE-01 and DONE-02 are unaffected and remain open
(see 61-06).

The later review-repair wave touched this area again; see the "Review-repair wave (2026-10-09)" section of `61-03-SUMMARY.md` for those repairs.
