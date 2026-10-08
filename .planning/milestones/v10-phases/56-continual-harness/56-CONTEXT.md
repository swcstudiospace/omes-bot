# Phase 56: Continual harness port - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous

<domain>
## Phase Boundary

Port Prime's continual harness: durable supplemental state (prompt notes,
memories, skill descriptions, subagent specs, factory specs) that the
agent refines through small, evidence-backed updates, session-local by
default with an opt-in global scope, every applied refinement snapshotted
with rollback. In scope: `omega_prime/learning/harness.py` (state store),
`omega_prime/agent/refine.py` (the refine pass), rostered tools, tests.
Out of scope: LLM-driven refinement planning (Prime's pa-core refinement
planner is model-driven; Omega's port keeps the deterministic
evidence-rule the curator already uses — the v1 Phase 4 precedent), the
factory spec runner (post-55 follow-up), auto-refine scheduling (Phase 57
attaches it to compaction arms).

</domain>

<decisions>
## Implementation Decisions

1. **State model mirrors Prime's exactly** (`rlm/harness.py`):
   kinds = prompt | memory | skill | subagent | factory; scope = local
   (session) default, global opt-in; store file `harness_state.json` under
   a `harness/` dir; strict entry-shape validation per kind; refinement
   events require trigger + changes + evidence + outcome (evidence is
   mandatory — the "evidence-backed updates only" rule).
2. **Snapshots + rollback:** every successful refine appends a snapshot of
   the prior state; `harness_rollback` restores the exact prior bytes.
   (Prime records refinement history for rollback; Omega makes rollback a
   first-class tool so the behavior is testable hermetically.)
3. **Base prompt immutability is test-enforced** (HARN-04): a refine pass
   never touches `prompts/` or the assembled prompt bytes — harness state
   is *supplemental*, injected as its own layer/section, and the
   `[harness-digest]` rides as a separate user message (Prime's layering
   contract) rather than a rewrite of the system prompt.
4. **Curator integration:** the existing curator decides *when* a turn
   earned a refinement (deterministic earn rule); the harness decides
   *what* can be written and how it's validated. Curator writes go through
   the harness store (the v1 Phase 4 rule "writes through the skill
   manager" generalizes to "through the harness store").
5. **Locking:** single-process Omega Prime needs no lock-dir; the store
   keeps an mtime-check on save to refuse clobbering a concurrently
   edited file (a cheap port of `_sync_from_disk`'s intent).

</decisions>

<code_context>
## Existing Code Insights

- `omega_prime/agent/curator.py`: post-turn earn rule + skill writes.
- `omega_prime/learning/`: autolearn.py (capture after substantive turn),
  advisor.py, goals.py — the harness store lands beside them.
- `omega_prime/memory/store.py`: MEMORY.md/USER.md entry model with char
  limits — harness `memory` kind entries reference, not duplicate, this
  store.
- `omega_prime/skills_runtime/manager.py`: skill create/edit/patch with
  frontmatter guards — harness `skill` kind entries describe skills; the
  manager remains the writer of skill files.
- `omega_prime/assemble.py` + `prompts/`: deterministic layered assembly;
  the supplemental layer is added here behind the harness config flag.
- Prime source: `rlm/harness.py` (HarnessState, validation, locking),
  `pa-core/src/refinement/` (planner/executor/ranking — model-driven;
  not ported), `pa-daemon/src/compact_autorefine.rs` (scheduling; Phase 57).

</code_context>

<specifics>
## Specifics

**New tools (family `harness`):** `harness_upsert`, `harness_get`,
`harness_list`, `harness_delete`, `harness_refine` (run a review pass over
the current trajectory and apply evidence-backed updates),
`harness_rollback`. Writes ⇒ `requires_approval` per precedent.

**Tests (`omega_prime/tests/test_harness.py`):** CRUD + validation per
kind; local/global scoping; refine applies only evidence-backed changes
and records a snapshot; rollback restores exact prior state; base prompt
bytes unchanged (assemble twice around a refine, diff); mtime clobber
refusal; disabled-family absence (config flag `prime.harness.enabled`,
default off).

**Acceptance:** v10-REQUIREMENTS HARN-01..04; full suite + evals +
assemble check green.

</specifics>
