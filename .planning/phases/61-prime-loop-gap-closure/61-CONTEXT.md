---
phase: 61-prime-loop-gap-closure
status: discussed
scope: v10-existing-requirements-gap-closure
---

# Phase 61: Prime loop gap closure — Context

## Scope boundary

Resume the existing v10 requirements, not a new product milestone. User said
"continue" after the recommended v10 gap-closure option; proceed conservatively
with that option. The archived Phase 57 library tests did not prove production
turn hooks or heartbeat re-entry. Close LOOP-01/02/03/06 and preserve
LOOP-04/05/07. Reconcile DONE-01/02 only after exercised verification.

The pre-existing native provider/catalog bridge remains intact. Do not replace
the Hermes/Omp loop with a native SessionEngine, patch upstream trees, launch an
agent/daemon subprocess, or broaden scope into TUI/daemon architecture.

## Locked implementation decisions

- Keep `Agent` / `run_conversation` as the one loop. Add optional Prime turn
  hooks; their default is absent. `OmegaPrimeAgent` binds enabled capabilities
  from the same registry that owns approvals, policy, and offered tools.
- Reuse `PrimeGoalStore`, `AutonomousDriver`, `guarded_hook`, `JobStore`, and
  APScheduler. No second goal store schema, autonomous state machine, or
  scheduling convention.
- Add one generic `ToolRegistry.runtime_bindings: dict[str, Any]`, empty by
  default. Registration publishes the resources already used by the tools;
  runtime consumption never bypasses `registry.dispatch` or grants tools.
- Binding keys: `prime_goals` is a zero-argument factory returning a freshly
  loaded `PrimeGoalStore`; `prime_autonomous` is the existing per-registry
  `{"driver": AutonomousDriver | None}` holder; `prime_heartbeat` is a
  `HeartbeatRuntime` instance. Disabled registration publishes no binding.
- Goal reads reload at boundaries so goal_set/pause/resume/clear and external
  completion are immediately authoritative. Accrue all model-call usage once
  per logical turn, including tool-call rounds. Native provider metadata must
  remain lossless. Unknown usage remains unknown/zero, never fabricated.
- Implicit continuation preserves the original transcript, system prompt,
  journal, pause/steer behavior, and session lease. It must not refill the
  outer model-call cap or a caller-supplied iteration budget. Explicit
  interrupt, failed/incomplete turns, paused/completed/stale/exhausted goals,
  and autonomous stop/quality-gate outcomes take precedence over continuation.
  Clearing a goal being worked in the current run cancels implicit re-entry;
  never-set absence does not veto independently enabled autonomy.
- Separate once-per-logical-turn accounting from permission to continue.
  Paid model calls remain charged at outer-cap/tool-row/failure boundaries;
  terminal accounting does not run a completion gate or append another prompt.
- Runtime hook failures use `guarded_hook` and structured redacted events;
  a degraded control hook prevents further implicit calls in that public run
  while retaining the normal response. Do not swallow provider errors,
  KeyboardInterrupt, SystemExit, or ordinary policy/approval refusal.
- Heartbeats target named live agent instances and preserve those instances'
  transcripts. Unknown names are explicit errors, never a fresh conversation.
- Extend `SessionLease.acquire` with keyword-only `wait: bool = False`. The
  existing fast-fail default stays unchanged. Heartbeat runs wait atomically
  for the lease; foreground callers retain the existing failure behavior.
  `run_conversation` / `OmegaPrimeAgent.run` can pass an opt-in wait keyword.
- `HeartbeatRuntime(path)` exposes
  `bind(name, runner, *, event_sink=None)`,
  `unbind(name, *, runner=None, stop_if_empty=False)`, `start()`,
  `stop(wait=True)`, `schedule()`, `list_jobs()`, `clear()`, and `close()`.
  The runner receives a prompt and returns the actual run result/response.
  It owns the persisted heartbeat job path and an APScheduler-backed lifecycle.
  Tool updates synchronize the real scheduler without losing persisted state.
  A binding's runner and optional sink are captured together for each beat;
  another named session must not overwrite that session's error-event owner.
  The constructor's optional service sink is for undirected diagnostics only.
  Conditional unbind compares the expected runner atomically: closing a
  replaced agent must not detach its replacement or stop another live binding.
  `stop_if_empty=True` combines conditional removal with last-owner shutdown;
  the emptiness decision must not race a replacement/concurrent binding.
  Waiting shutdown settles overdue-start callbacks as well as scheduler jobs,
  and a superseded start cannot restart scheduling after close.
  An overlapping start during an active drain raises rather than reporting
  success. A later explicit stop/close cancels an older conditional restart;
  only the latest eligible last-owner cleanup may resume a replacement.
- `OmegaPrimeAgent` owns the glue: an optional stable `session_name` defaults
  to `default`; when a heartbeat binding exists, bind its live runner before
  starting the runtime. Provide close/context-manager lifecycle; closing the
  last binding stops owned scheduling. Never start threads when flags are off.
  Its heartbeat callback returns the actual final response, not a live
  transcript alias. Cleanup failures propagate and keep a retryable handle.
- Never hold a JobStore/bookkeeping lock while waiting for a session lease or
  running a model/tool callback: a foreground heartbeat tool call would
  otherwise deadlock with the background scheduler. Claim/update bookkeeping
  and callback execution are separate. Clear/schedule during an active beat
  must not resurrect cleared jobs or overwrite another tool's update.
  Due-now projection sets the next run explicitly so an interval beat does
  not wait one full interval. Calendar projection preserves injected clock
  semantics relative to the scheduler's wall clock.
- Integration review refinements: non-JSON beat results produce a structured
  error and a redacted degradation event, never a `repr` success fallback.
  Start/restart reconciles scheduler entries with current persisted heartbeats;
  foreign cron kinds are untouched. Enabled re-registration reuses the same
  registry-bound runtime for the same resolved job path. The supported single
  runtime/registry authority is shared by named sessions; no new global cache,
  second agent service, or multi-registry runtime architecture is introduced.
- No additional continuation-round cap: the existing cumulative model-call
  cap and iteration budget remain authoritative. Known usage from successful
  model calls is accrued even when a later call fails; provider exceptions
  retain their original type/propagation and must not become degradation-only
  outcomes. Completion regressions use an external store handle, since no
  goal-complete tool exists.

## Ownership / execution units

1. Loop boundaries: conversation_loop, runtime, generic registry attachment,
   goals/autonomous registration, optional Prime hook module, and focused
   loop integration regressions. This unit owns runtime.py integration glue.
2. Heartbeat scheduling: heartbeat runtime, APScheduler integration,
   heartbeat tool registration, SessionLease waiting, and focused scheduler /
   serialization regressions. Do not edit runtime.py or ToolRegistry here;
   consume the locked interfaces and notify the loop owner of deviations.

Both units may implement concurrently after plan-checker acceptance because
interfaces and writable ownership are disjoint. Parent is the sole planning
state integration owner. Agents skip builds, tests, lint, typechecks,
formatters, commits, and publication; parent runs final checks after integration.

## Verification / acceptance

Before changes, run a throwaway real-loop reproduction of registered active
state being ignored. After integration, exercise actual OmegaPrimeAgent turns
and real APScheduler heartbeats, including foreground overlap and on-disk
history. Tests must catch consumer-visible boundary bugs (caps, pause/stop,
usage, degradation, routing/serialization), not source-text or wiring assertions.

Parent runs affected regressions, full Python tests, Ruff, mypy, evals, prompt
assembly/catalog checks, and setup check. Reuse the existing Python environment
and sandbox HOME/XDG conventions. No Rust source changes are planned; do not
rerun the documented upstream ext4 baseline failures to reconfirm them.

Update docs and milestone claims only after smoke evidence. Existing uncommitted
work is preserved. No commits or shipping until finished work ownership and the
Ultrathink readiness gate permit them.

## Original61-01/02 gate results before broader integration audit

- Pre-repair gates:234 affected tests and686 full-suite tests passed;
  26 evaluations, Ruff, formatter, mypy, assembly/catalog/setup, actionlint
  and lockfile pip audit returned exit0. These receipts remain valid for the
  exercised snapshot, not blanket literal32-requirement acceptance.
- Real native HTTP/scheduler paths and real Anthropic parsing/gates are
  exercised. Per-call budget totals preserve mixed-shape paid work without
  rewriting public/native usage; later interrupts preserve the accepted answer.
- Malformed identifiable heartbeats diagnose once and disarm. Invalid,
  unrepresentable or nonadvancing calendars are rejected before persistence.
  Injected foreign entries survive; a dead injected pool cannot restart
  silently. Actual delayed native delivery catches up once.
- Parent review/audit repairs the inherited pre-refine snapshot ordering and
  adds fixed-base-prompt behavior proof. Generic JobStore/backend behavior and
  schemas remain unchanged; the shared heartbeat helper only gains safe
  malformed-row filtering.
- Nine native license headers, tracked license policy and independent native
  build/license CI are added. The header-only bridge is rebuilt; native
  function/ABI and ignored upstream logic are unchanged. Known vendor Rust
  exit-101/ext4 receipts are retained, not rerun.
- REPO-04 remains open: Cargo Dependabot cannot fetch the ignored required
  path manifests. A complete source-only Cargo resolution proves the missing
  crossterm manifest (exit 101). The user must authorize pinned repository-
  fetchable dependency sources or an explicit Cargo automation scope exception.
  No native engine/daemon work is inferred from that packaging decision.
- DONE-01/02, archive/cleanup and publication remain pending. Historical phase
  directories 53–60 and their imperfect legacy metadata stay frozen.


## Cross-phase literal gaps and bounded repairs

The exact independent integration checker finds22WIRED/10BROKEN of32 criteria
in61-INTEGRATION.md. RLM-03/04, LOOP-05/07, CONN-01/03 and REPO-05 are explicitly
reopened alongside REPO-04/DONE. Actual before smoke proves boolean model
admitted, answer in list,0-byte child session, no recovered children, always
accepted unbound progress, and disabled RLM name in assembled prompt. Isolated
source without Prime reproduces missing manifest/runtime import. Local tests
did not cover those consumer boundaries.

- Plan03 owns typed connector modules and registered tools; policy then
  approval remains authoritative, decoding before authorized side effects.
- Plan04 owns core RLM and existing kernel host. Reuse atomic versioned
  session/persist.py; recover real terminal children without parent input
  leakage or fabricated interrupted completion. Child-bound progress uses
  real ownership/throttling. List/delete are metadata-only; collect owns answers.
- Plan05 owns static bot roster/prompt assembly/catalog. Family-name membership
  is frozen; retain render's two-argument API with optional config. Canonical
  default-off generation never depends on user's HOME flags.
- ParentPlan06 owns authentic historical oracle and out-of-scope composition/
  docs/CI. Final current checks wait for all wave2 repairs. Commit79ff51af is
  the observed direct parent of first v10 commit70babccf, not an invented
  v9-final tag; its source execution captured six baseline consumer transcripts.
- Frozen RLM connector additions:CreateSessionRequest/DeleteRequest/
  RenameRequest, create_session/delete_subagent/rename alongside existing
  spawn/collect/list_subagents/progress_note. One writer, read-only kernel consumer.
- New nine plan-authored threats are not verified merely because the original
  register had15 closed findings. Expanded validation/security gates rerun
  against actual integrated runtime evidence before any lifecycle claim.


## Closeout decisions (2026-10-09, user)

- **LOOP-07:** documented criterion exception accepted. The transcript-fixture half passes 6/6
  against a pristine pre-v10 checkout; the unmodified historical suite replays as 376 passed /
  2 failed (catalog/roster inventory pins), identical before and after the review-repair wave.
  No test is edited, deleted or shimmed.
- **REPO-04:** criterion exception accepted, no Cargo Dependabot (the Cargo path dependencies
  live in the ignored read-only prime-agent checkout; source-only `cargo metadata --locked`
  exits 101). cargo-deny and pip-audit run; pip and github-actions Dependabot are configured.
- **CONN-01:** documented scope accepted: every registered Prime tool of seven families and the
  kernel bridge's declared keys decode through versioned typed requests; loop-internal goal
  accrual and driver consult use the live store/driver with typed response views.
- **Lifecycle:** stop before the irreversible lifecycle. No milestone completion, archive,
  cleanup, commit or PR. Open: REPO-05 (published revision or acceptance of the isolated
  snapshot evidence), DONE-01, DONE-02.
