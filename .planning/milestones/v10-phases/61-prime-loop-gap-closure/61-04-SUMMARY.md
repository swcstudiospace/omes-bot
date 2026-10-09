---
phase: 61-prime-loop-gap-closure
plan: "04"
subsystem: rlm-children
tags: [rlm, durable-sessions, child-bound-progress, collect-only-answers, kernel-host]
status: product_verified_review_repaired
requires:
  - phase: 55
    provides: In-process RlmHost, spawn/collect/list/delete/rename/progress-note port and Prime status vocabulary
  - phase: 58
    provides: Typed versioned RlmConnector request/view boundary (extended read-only by Plan 03)
  - phase: 61-03
    provides: CreateSessionRequest, DeleteRequest, RenameRequest and strict registered handlers
provides:
  - Child sessions persisted as atomic versioned session documents holding the real prompt, answer, identity, owner and status
  - Fresh-host recovery that never replays an interrupted child and never reports it done
  - Kernel rlm.progress.note routed through the owning parent's length and 10-second acceptance logic, bound to the executing child
  - Metadata-only list/delete across registered tools and kernel replies; the answer is visible only through collect
  - Kernel RLM operations crossing the existing RlmConnector boundary with no invented model selector
affects: [61-06, v10-closeout]
tech-stack:
  added: []
  patterns: [session/persist.py atomic save, thread-local child binding, settled-on-disk barrier, delete tombstone]
key-files:
  modified:
    - omega_prime/agent/rlm.py
    - omega_prime/prime_kernel/host.py
    - omega_prime/tests/test_rlm.py
    - omega_prime/tests/test_prime_kernel_host.py
    - omega_prime/tests/test_prime_kernel_cells.py
key-decisions:
  - "Reuse omega_prime/session/persist.py save_session/load_session; no second persistence convention and no touched-empty JSONL file."
  - "A child is reported done only after its terminal document is on disk; a failed terminal save becomes an error, never a fake completion."
  - "Kernel child identity comes only from the worker thread's bound context; payload child ids are ignored and an unbound root note is accepted=false."
  - "The host never invents a model selector: explicit request selector, then operator-configured InProcessHost model, then an explicit error before any child exists."
requirements-completed: [RLM-03, RLM-04]
requirements-open: []
coverage:
  - id: durable-child-sessions
    description: Fresh host recovers the persisted prompt, answer and status; interrupted/failed children recover as explicit errors without replay; deleted children are not resurrected
    requirement: RLM-03
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_kernel_consumer_smoke
        status: pass
      - kind: integration
        ref: 61-EVIDENCE.json#post_followup_durable_delete_after
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_rlm.py
        status: pass
    human_judgment: false
  - id: child-bound-progress
    description: A child's note updates its parent-side snapshot through the real acceptance logic and a second note inside ten seconds is throttled; unbound or spoofed kernel notes are rejected
    requirement: RLM-03
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_kernel_consumer_smoke
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_prime_kernel_host.py
        status: pass
    human_judgment: false
  - id: collect-only-answers-and-isolation
    description: The parent's private marker never reaches the child; the child's answer is absent from list/delete and present in collect
    requirement: RLM-04
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_kernel_consumer_smoke
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_prime_kernel_cells.py
        status: pass
    human_judgment: false
completed: 2026-10-09
---

# Plan 61-04 — Recoverable RLM child sessions, owned progress, collect-only answers

`RlmDurabilityRepair` executed the five-file source slice (retained as plan label
`61-04-followup`) with no mid-flight checks or commits; the parent integrated the
delivery, ran every gate, and added two deterministic delete/settle transition
regressions after its own diagnostics found a resurrection race (see below). This
summary is not a full32 or signed A09/A10/A11 gate. Code descriptions below come from
reading the final tree; the later review-repair wave changed this area further and is
described only in the 61-03 summary.

## Delivered behavior

**Durable child sessions (RLM-03).** `RlmHost._persist_child` calls the existing
`save_session` (atomic, versioned) with the child's real user prompt, its assistant
answer once known, and metadata `kind=rlm-child`, `rlm_child_id`, `name`, `model`,
`status`, `error` and the owning `parent` name. Only the child prompt is stored, never
parent conversation text. `spawn` and `create_session` share one admission path
(`_admit`) with a uuid session id, so the `session_file` returned by `create_session`
is the real recoverable `.json` document, not a touched empty file. Roster rows and
typed views carry `session_id` and `active_session_id`. The `RlmHost` constructor runs
`recover_all()`; `recover_session` reconstructs completed and failed documents as
settled records without rewriting them. A document still marked `running` recovers as
an explicit error (`interrupted: ... not replayed`), its worker is never re-executed
and that single status change is persisted (a failed write leaves an in-memory error
that names it). Foreign-owner, legacy-unowned and deleted records are refused or
skipped. A `settled_on_disk` event gates `done` in `status()`, `to_result()` and the
bounded `collect`, and a failed terminal save settles as an error. Delete writes a
prompt/answer-free tombstone under the persist lock so a late settle cannot resurrect
it; rename re-persists lifecycle status with rollback.

**Child-bound progress (RLM-03).** `_admit` registers the child identity before the
worker is submitted. `_run_bound` binds the identity to the worker thread
(`threading.local`) and passes a `progress` callback only to runners that declare one.
`RlmHost.progress_note` applies the 512 UTF-16-unit cap and the 10-second throttle and
updates the parent-side snapshot. The kernel handler `InProcessHost._progress_note`
ignores any child id in the payload; identity is `RlmHost.current_child_id()` on the
calling thread, and an unbound root note returns `accepted=false, retry_after_ms=null`.
The registered `rlm_progress_note` tool keeps its explicit-`child_id` contract.

**Collect-only answers (RLM-04).** `_Child.to_subagent` sets `answer_preview=None`;
the typed list view `_subagent_view` omits `answer_preview`; the kernel delete reply
is a metadata snapshot (`_metadata_snapshot` strips any answer key) taken before
deletion. `collect` still returns `ChildResultView.answer_preview` only with a terminal
status. The child agent in the smoke receives only the child prompt.

**Kernel boundary.** `InProcessHost` builds one `RlmConnector` and routes
`rlm.run/create_session/collect/list_subagents/delete_subagent/rename/progress.note`
through it, decoding each with the strict `Request.from_dict` (bad boolean model, missing
name, non-object kwargs, bad timeout fail before any child exists). `_resolve_model`
uses the explicit request selector, then an operator-configured `InProcessHost(model=...)`,
else raises before spawn/create; `rlm.find_models` advertises nothing. The production
constructor in `tools/prime_runtime.py` passes no default model, so a kernel
spawn/create there needs an explicit model selector.

## Actual verification

Observed before (`61-EVIDENCE.json#cross_phase_before`, exit 0): created session
`durable_session_bytes` 0, `recovered_children` 0, two kernel progress notes both
`accepted: true`, a boolean `model` admitted, and the child answer present in list.
Parent diagnostics on the delivered slice
(`#post_slice_kernel_remaining_before`, `#post_slice_durable_settlement_before`) found
a boolean-model kernel run still admitted, an unbound named-child note accepted, and
collect reporting `done` while the persisted status was still `running` (fresh host
recovered 0 children); those were fixed in the same files. Their separate after-reruns
are not keyed; the after state is covered by the smoke and tests below.
`#post_followup_durable_delete_before` showed a delayed terminal callback resurrecting a
deleted child (`status_after_delayed_terminal_callback: completed`, fresh host 1 child)
and a failed tombstone hiding the child; `#post_followup_durable_delete_after`
(same event-barrier script, exit 0) shows `deleted`, 0 fresh-host children, and the
child still visible after an injected tombstone failure.

`#cross_gap_actual_kernel_consumer_smoke` (exit 0, no pytest, scripted explicit child
runner, real `OmegaPrimeAgent` child): the real child's model request contained only
the system prompt and `child-only-task`; `PARENT-PRIVATE-MARKER` is absent from the
child requests and the persisted document; bound progress `accepted: true` then
`throttled: true` with `retry_after_ms` 9999; unbound named-child spoof
`accepted: false`; boolean model and missing selector return error envelopes with zero
children; `PRIVATE-CHILD-ANSWER` is absent from the raw list reply and present in
collect; the persisted document has `status completed` and messages
`[user child-only-task, assistant PRIVATE-CHILD-ANSWER]`; a fresh `InProcessHost`
collects the child as `done`; after delete a new host lists none. Its recorded scope is
an explicit caller-selected scripted fixture, not a native model or automatic engine.

Integrated gates after Plans 03-05 (`#cross_gap_current_full_python`): full suite
739 passed, 12 warnings, exit 0. Fresh isolated install
(`#isolated_current_full_suite_after`): 726 passed, 13 skipped, 12 warnings, setup
exit 0. Static (`#cross_gap_final_static`): Ruff 0, 271 files formatted, mypy 236
sources 0, 26 evals, actionlint 0. The first affected-suite run
(`#cross_gap_affected_first`, 356 passed / 3 failed) failed on three test assertions,
recorded as an obsolete `.jsonl` suffix pin in a lifecycle test and two
escaped-JSON/timeout-cleanup assertions in a failure test, which the parent fixed or retired. Named regressions read in the final tree:
`test_rlm.py` (fresh-host recovery of completed/failed/interrupted children, bound
progress isolation, collect-only answer, delete not resurrected, terminal storage
failure is error), `test_prime_kernel_host.py` (unbound/spoofed note rejected, bound
note throttles, create_session returns a real file, strict model failures),
`test_prime_kernel_cells.py::test_cell_child_answer_visible_only_through_collect`.

## Parent corrections and limitations

Parent replaced fixed-sleep collect tests with event-controlled transitions and fixed
the delete/settle ordering so terminal publication happens under the existing durable
lock (`#cross_gap_parent_lifecycle_fix`). The retained evidence shows RLM-03 and
RLM-04 satisfied for an explicitly supplied child runner: the default native
`run_child=None` path is an explicit "no child runner" error, not child delivery, and
is not claimed. Self-rename can leave partially re-stamped children if storage fails
mid-loop (executor-reported; storage failure still surfaces loudly). No signed
A09/A10/A11 verdict, cloud CI pass or published-clone proof exists for this plan.
Literal LOOP-07, REPO-04, REPO-05, DONE-01 and DONE-02 are unaffected and remain open
(see 61-06).

The later review-repair wave touched this area again; see the "Review-repair wave (2026-10-09)" section of `61-03-SUMMARY.md` for those repairs.
