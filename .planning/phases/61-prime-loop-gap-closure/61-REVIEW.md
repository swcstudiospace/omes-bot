---
phase: 61-prime-loop-gap-closure
reviewed: 2026-10-09T18:00:00Z
depth: deep
files_reviewed: 21
files_reviewed_list:
  - omega_prime/prime/types.py
  - omega_prime/agent/conversation_loop.py
  - omega_prime/agent/goals.py
  - omega_prime/agent/rlm.py
  - omega_prime/agent/runtime.py
  - omega_prime/agent/turn_tool_round.py
  - omega_prime/assemble.py
  - omega_prime/prime/autonomous.py
  - omega_prime/prime/goals.py
  - omega_prime/prime/heartbeat.py
  - omega_prime/prime/kernel.py
  - omega_prime/prime/messaging.py
  - omega_prime/prime/rlm.py
  - omega_prime/prime_kernel/host.py
  - omega_prime/tools/agent_message.py
  - omega_prime/tools/autonomous.py
  - omega_prime/tools/goals.py
  - omega_prime/tools/harness.py
  - omega_prime/tools/heartbeat.py
  - omega_prime/tools/prime_runtime.py
  - omega_prime/tools/rlm.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 61: Post-Repair Code Review (prime-loop-gap-closure)

**Reviewed:** 2026-10-09
**Depth:** deep (cross-file; read-only; no test suites, linters, formatters or builds were run: `checks_run = []`)
**Files Reviewed:** 21
**Status:** clean (0 open findings — this pass raised 2, both closed; see Verification of WR-15 fix)

This report replaces the earlier `61-REVIEW.md`; that report is preserved at
`.planning/phases/61-prime-loop-gap-closure/61-REVIEW-pre-repair.md` (2 critical,
14 warning, 5 info findings, IDs CR-01..IN-05). Every prior ID is dispositioned
below with file:line evidence.

## Scope and method

Explicit file scope is the `files_reviewed_list` above (the 21 files changed by
the repair wave). Also read for tracing only: `omega_prime/tools/registry.py`,
`omega_prime/agent/runtime.py` (in scope; dispatcher read for the loop path),
`omega_prime/cron/heartbeat_runtime.py` (schedule validation),
`omega_prime/learning/goals.py` (store invariants via `agent/goals.py`),
`omega_prime/prime/harness.py` (in scope; full decoder read),
and the new/changed tests `test_prime_loop_boundaries.py`,
`test_prime_goal_surface.py`, `test_prime_tool_surface.py`,
`test_prime_rlm_surface.py`, `test_prime_heartbeat_boundary.py`,
`test_prime_kernel_boundary.py`, `test_prime_tool_authorization.py`,
`test_agent_message.py`, `test_rlm.py`, `test_goals_prime.py`, `test_shell.py`
(read for seam/behavior verification, not re-reviewed for style).

Evidence classes: **[source]** = verified in current source, **[repro]** = confirmed
by a throwaway script I ran (see Reproduction log; scripts live outside the repo
tree in `/tmp/p61repro/`, run with
`PYTHONPATH=/root/src/repos/omega-prime` under the repo venv),
**[inference]** = reasoning from code that was read but not executed.
No test suite, linter, formatter or build was run.

## Summary

The repair wave holds. Both pre-repair blockers are closed through the real
consuming paths and pinned by consumer tests: session-bound messaging identity
can no longer be forged or overridden, and unparseable tool-call arguments are
error rows, never executed defaults. The handler convention is uniform across
all seven tool families (`reject_extra` first, required params default `None`,
no `PrimeError` caught in any handler), the registry converts typed failures to
the `{error, code, reason}` envelope audited as `error` with `<code>: <reason>`,
policy precedes approval precedes decode, and the RLM host was rebuilt around a
consistent persist-outer/registry-inner two-lock discipline with atomic
admission, tombstone-wins settlement, done-gated collect rows, and
recovery that only writes on interruption.

This pass raised one warning and one info item, both narrow, and both are
now closed (0 remain open): whitespace-only strings passed the shared
`require_str` gate and failed deeper as untyped errors (WR-15 — repaired
and re-verified, see Verification of WR-15 fix), and a blank progress note
is accepted and stored (IN-06 — conscious non-change per the pinned Prime
contract, which bounds only length and rate). No side effect occurred in any
of these paths. No critical defects were found in either pass.

## Prior findings disposition

### CR-01: Messaging identity override — RESOLVED

**Evidence [source]:** `omega_prime/tools/agent_message.py:67-84` — both handlers
take only their declared parameters plus `schema_version` and `**extra`, call
`reject_extra(extra, ...)` first, and build the request exclusively from the
session bound at registration (`"sender": session` at :74,
`"session": session` at :78). There is no merge of model input into the bound
fields: `agent_message_send {"sender": "<other>"}` and
`agent_observe {"session": "<other>"}`, `{"mark_read": false}` are all
`unknown_field`. The connector maps failures by cause
(`omega_prime/prime/messaging.py:119-140`: `bad_value` for empty body,
`unknown_sender`, `unknown_recipient` with the members hint only on the
recipient branch, `unknown_session` on observe).
**Pinned by tests [source]:** `test_agent_message.py:188-224`
(`test_loop_send_cannot_forge_the_sender`,
`test_loop_observe_rejects_undeclared_mark_read_and_leaves_inbox_unread`,
cross-session read leaves the other inbox unread).

### CR-02: Unparseable arguments executed as `{}` — RESOLVED

**Evidence [source]:** `omega_prime/agent/turn_tool_round.py:94-106` — `_arguments`
returns `({}, None)` only for `None`/`""`; every other malformed or non-object
payload (truncated JSON, list, number, `null`, whitespace-only, non-str types)
returns `({}, "<problem>")`, and `run_tool_round` (:38-58) turns the problem
into an `error:` row for that call only without executing it.
**[repro]:** exercised all 13 shapes (`None`, `""`, `"   "`, `"null"`, `"[]"`,
`"42"`, `'"hi"'`, truncated object, valid object, `42`, `["x"]`, dict,
duplicate keys) — only `None`/`""`/valid-object/dict decode clean; the rest
are problems, never executed. Duplicate keys resolve last-wins per stdlib
`json` (checked, sound — see below).
**Pinned by tests [source]:** `test_prime_loop_boundaries.py` (truncated
arguments, 10-shape non-object parametrize, malformed-call-alone-in-round),
all through the real `OmegaPrimeAgent.run` with a persisted-store read-back.

### WR-01: Omitted required fields bypass typed decoders — RESOLVED

**Evidence [source]:** every handler in `tools/rlm.py:76-170`,
`tools/harness.py:84-190`, `tools/goals.py:69-100`,
`tools/agent_message.py:67-84`, `tools/autonomous.py:71-100`,
`tools/heartbeat.py:69-100`, `tools/prime_runtime.py:82-170` declares required
parameters with `None` defaults (`prompt: Any = None`, `target: Any = None`,
`command: Any = None`, `args: Any = None`, …), so omission reaches
`require_str`/`require_int` as `bad_type`, never a Python `TypeError`.
**Pinned by tests [source]:** omitted-field cases in `test_prime_tool_surface.py:189`
(harness), `test_prime_heartbeat_boundary.py:192` (all three required),
`test_prime_kernel_boundary.py:107` (all tools), `test_prime_rlm_surface.py`
(omitted + loop recovery), `test_prime_loop_boundaries.py`.

### WR-02: Handlers swallow `PrimeError`, audit says `allowed` — RESOLVED

**Evidence [source]:** grep over `omega_prime/tools/` shows no `except PrimeError`
in any handler — only `raise PrimeError` (`tools/harness.py:55`, the `_scope`
bool guard) and comments. `ToolRegistry.dispatch`
(`omega_prime/tools/registry.py:89-131`) owns the single `except PrimeError`
branch (:106-113) returning `exc.to_dict()` and recording
`("error", "<code>: <reason>")` (:111). Order is policy (:99) → approval (:103)
→ decode (:105).
**Pinned by tests [source]:** `test_prime_tool_surface.py:213-220`
(`test_typed_failure_is_audited_as_error`), `test_prime_rlm_surface.py:146-164`.

### WR-03: Undeclared `scope` alias overrides `global_` — RESOLVED

**Evidence [source]:** `tools/harness.py:48-58` (`_scope` rejects non-bool,
never truthy-coerces) plus `reject_extra` as the first statement of all six
harness handlers (:94, :115, :135, :152, :171, :190); the payload's `scope`
comes only from `_scope(global_)`. A `scope` key is `unknown_field`.
**Pinned by tests [source]:** `test_prime_tool_surface.py:101-145` (all three
scope spellings plus override attempt, both stores stay empty) and the loop
variant at :278-298.

### WR-04: `goal_set` non-atomic, stale return, step inheritance — RESOLVED

**Evidence [source]:** `SetGoalRequest.from_dict` (`omega_prime/prime/goals.py:47-68`)
rejects non-list steps (`bad_type`) and blank steps (`bad_value`) before any
store touch. `PrimeGoalStore.replace_goal` (`omega_prime/agent/goals.py:88-126`)
validates objective (non-blank), budget, and every step up front, then replaces
objective **and** steps (no inheritance) and returns `prime_status()` after the
write (steps visible in the result). `goal_set` passes no `stale_after_turns`
(`tools/goals.py:69-84` has no such parameter → `unknown_field`).
**Pinned by tests [source]:** `test_prime_goal_surface.py:80-98` (blank step →
`bad_value`, stored goal untouched, fresh store writes nothing),
`:148-165` (`stale_after_turns` is not a tool argument, writes nothing).
The crash-between-the-two-file-writes window is now documented in the
`replace_goal` docstring (:96-126) as a stated non-goal, not a silent gap.
One residual whitespace path remains — see new finding WR-15.

### WR-05: `max_minutes` NaN/Infinity disables the bound — RESOLVED

**Evidence [source]:** `StartRequest.from_dict`
(`omega_prime/prime/autonomous.py:60-90`) rejects bools, non-numbers,
non-finite floats (`math.isfinite`), and non-positive values as `bad_value`;
`optional_int` rejects bool budgets. Config-supplied values merge **before**
decoding (`tools/autonomous.py:71-100`), so a poisonous config value is also
a typed error with no run started.
**Pinned by tests [source]:** `test_prime_tool_surface.py:234-251` (direct and
from-config `inf`), plus finite-acceptance cases.

### WR-06: Implicit RLM parent contract — RESOLVED

**Evidence [source]:** `require_parent` (`omega_prime/agent/rlm.py:250-270`)
demands exactly `session_dir` (non-empty str/PathLike), `session_name`
(str/None), `delegate_depth`/`max_depth` (int ≥ 0), `max_children` (int ≥ 1)
with no defaults; enforced at `RlmHost.__init__` (:313) and at
`register_rlm_tools` when a parent is given (`tools/rlm.py:45-60`).
`OmegaPrimeAgent` accepts `session_dir=` (`omega_prime/agent/runtime.py`) and
the `Agent` base carries `delegate_depth`/`max_depth`/`max_children`
(`conversation_loop.py:112-114`); `_admit` reads the depth bound from
`delegate_depth` (`agent/rlm.py:583-656`). A real agent without `session_dir`
fails loudly (`TypeError`), never defaults to the process CWD.
**Pinned by tests [source]:** `test_rlm.py:703-753` (real-agent parent writes
only under its session dir with CWD proven empty, max-depth refusal writes no
session dir, missing-`session_dir` rejection, per-attribute contract matrix);
`test_growth.py:616` registers with a real `OmegaPrimeAgent(session_dir=…)`.

### WR-07: `rlm_create_session` cwd / recovery / roster ordering — RESOLVED

**Evidence [source]:** (a) `cwd` is not a handler parameter
(`tools/rlm.py:126-146`, comment at :133-135) → `reject_extra` yields
`unknown_field`; the decoder refuses a non-null `cwd` as `bad_value`
(`prime/rlm.py`, `CreateSessionRequest`, null tolerated for the pinned SDK).
(b) Single durable root: `_durable_dir()` (`agent/rlm.py:332`) derives only
from the parent contract; no per-call directory exists. (c) `create_session`
(`agent/rlm.py:872-919`) admits first (`_admit`, which durably records), then
calls `session_store.create`, and on failure reaps via `delete_subagent` —
a refused create leaves no roster row.
**Pinned by tests [source]:** `test_prime_rlm_surface.py:152-180` (cwd →
`unknown_field`, zero files under the session dir, `elsewhere/` never
created, roster rows empty; no-cwd persists under the parent directory).

### WR-08: Recovery rewrites terminal records; write failure kills the family — RESOLVED

**Evidence [source]:** `recover_session` (`agent/rlm.py:393-495`) reconstructs
terminal (`completed`/`error`/`failed`) records from disk without rewriting;
only the interrupted (`running`) → `error` transition persists, and its write
failure is absorbed into the in-memory error text (`child.error = "…;
recovery write failed: …"`, :490-492) — recovery never raises for it.
`recover_all` (:497-532) skips unreadable/non-child/foreign/deleted documents.
**[inference]:** failure-absorption paths are code-traced, not executed here;
the permanent suite carries persist-failure tests (unchanged contracts).

### WR-09: Delete tombstones retain prompt/answer — RESOLVED

**Evidence [source]:** `_persist_child` (`agent/rlm.py:339-383`) branches on
`child.deleting`: the tombstone writes `messages=[]` with identity/owner/status
metadata only (no prompt, answer, or error text); the docstring states the
tombstone exists solely to defeat resurrection.

### WR-10: `collect` shows answer/error on `running` rows — RESOLVED

**Evidence [source]:** `to_result` (`agent/rlm.py:219-248`) publishes
`answer_preview`/`error` only when `is_settled()` (future done **and**
`settled_on_disk` set); otherwise status is `running` with both fields `None`.
`to_subagent` (:198-217) keeps `answer_preview=None` on the roster channel.

### WR-11: Unsynchronized registry; delete races spawn — RESOLVED (redesigned)

**Evidence [source]:** two-lock discipline documented on `RlmHost`
(`agent/rlm.py:286-311`) and implemented consistently: every site takes
persist-outer → registry-inner (`_persist_child` takes persist only;
`delete_subagent` :762-793, `rename` :795-844, `recover_session` :393-495,
`recover_all` :497-532 all nest registry inside persist; `collect`/`_select`
(:706-756), `list_subagents` (:758-760), `progress_note` (:846-870) take
registry only and never do I/O or wait). Admission (`_admit`, :583-656) checks
name/limits/depth and registers under one registry section, then performs the
first durable write, the `deleting` re-check, and `executor.submit` under one
persist section — a child deleted during admission (`deleting` set under the
same persist lock by `delete_subagent`) raises before submit and never starts,
and its tombstone write is not clobbered (`_persist_child` honors `deleting`
over the passed status). `_settle` (:658-680) takes persist only, so it cannot
invert the order; tombstone-wins because the `deleting` decision and write are
one persist section. No lock is held while waiting on a future (`collect`
waits outside both locks). Post-registration reads of live `_Child` refs
outside the lock (`to_result`) are benign stale reads under the GIL
(no dict mutation, no corruption).
**[repro]:** 8-thread hammer over `list_subagents` + `collect` (80 dispatches,
live settled child) completed with zero errors.
`delete_subagent` cancels a pending future best-effort; a thread already
running cannot be killed (thread-model inherent) but `_settle` preserves the
tombstone — checked, sound (see below).

### WR-12: `_refusal_reason` poisons recovered turns — RESOLVED

**Evidence [source]:** `_refusal_reason`
(`omega_prime/agent/conversation_loop.py:461-492`) scans only tool rows after
the last assistant row carrying `tool_calls` within the run, and only rows
anchored on the failure wire (`content.startswith("error:")` — the
dispatcher-raised denial shape from `agent/runtime.py:30-37` via
`turn_tool_round._execute`). A recovered refusal is not terminal; a final-round
refusal still is.
**Pinned by tests [source]:** `test_prime_loop_boundaries.py:218-256`
(recovered → `completed is True`, exit reason not `approval_refused`;
final-round → `completed is False`, `approval_refused`).

### WR-13: `--enable-family` clobbers the canonical artifact — RESOLVED

**Evidence [source]:** `omega_prime/assemble.py:198-280` — `--output PATH` added;
`--enable-family` without `--output` is a hard error (`parser.error`, :231)
that writes nothing; with `--enable-family` the canonical
`prompts-assembled/OMEGA_PRIME.xml` is never the destination; `--check`
compares the same PATH it would write.
**Pinned by tests [source]:** `test_shell.py:192-237` (enabled output leaves
canonical bytes identical, missing `--output` refused with code 2 and zero
new files, plain `--output` redirect round-trips).

### WR-14: Permanent-test gaps — RESOLVED (with one documented exception)

**Evidence [source]:** the gaps enumerated pre-repair are now consumer-pinned:
bound identity (`test_agent_message.py`), truncated/non-object loop arguments
and refusal scoping (`test_prime_loop_boundaries.py`), omitted fields per
family (`test_prime_tool_surface.py`, `test_prime_heartbeat_boundary.py`,
`test_prime_kernel_boundary.py`, `test_prime_rlm_surface.py`), audit verdicts
(`test_prime_tool_surface.py:213`, `test_prime_rlm_surface.py:146`),
`scope` alias (`test_prime_tool_surface.py:101`, loop variant),
blank goal steps (`test_prime_goal_surface.py:80`), NaN budgets
(`test_prime_tool_surface.py:234`), policy/approval-before-decode ordering
(`test_prime_tool_authorization.py:223-268`, `test_prime_kernel_boundary.py:72`),
real-Agent parents (`test_rlm.py:703`), no-side-effect file assertions
(`tmp_path.iterdir() == []` / `rglob` emptiness across boundary suites).
**Consciously not changed:** `test_prime_regression.py` still drives a
test-local dispatcher (not `OmegaPrimeAgent._dispatcher`) — the historical
oracle fixture must stay byte-identical; its scope is documented rather than
migrated, and the registered-agent error rows are covered by
`test_prime_failure_injection.py` plus the new boundary suites. Not a defect.

### IN-01: Preview field / 200-char collect — CONSCIOUSLY NOT CHANGED

Per the repair brief: `RLMSubagent.answer_preview` mirrors the pinned SDK
shape and the 200-char `answer[:200]` preview (`agent/rlm.py:193-196`) is the
intended Prime semantic (full answer only in the session file). The roster
channel provably carries no answer text (`to_subagent`, :198-217). Not a defect.

### IN-02: `rlm_progress_note` explicit child selector — CONSCIOUSLY NOT CHANGED

The registered tool keeps its explicit `child_id` contract
(`tools/rlm.py:148-162`); same-principal forgeability is the documented shape.
Not a defect.

### IN-03: Version/timeout bounds — PARTIALLY FIXED, REMAINDER CONSCIOUS

**Fixed [source]:** `schema_version` 0/negative is now `bad_value`
(`prime/types.py:20-30`, `version < 1` branch), pinned per tool
(`test_prime_kernel_boundary.py:132`; heartbeat/history suites carry the
`unsupported_schema_version` parametrize). **Consciously not changed:**
`rlm_collect timeout_ms` has no upper bound (huge values decode fine —
verified `[repro]`) and does not observe the interrupt flag. Not a defect.

### IN-04: Process-global `rlm.repl` patching — CONSCIOUSLY NOT CHANGED

`InProcessHost.install/uninstall` (`prime_kernel/host.py:68-83`) still patches
module-global callables; affects multi-root embedders only. All `InProcessHost`
construction sites pass full-contract parents (tests carry
`session_dir/session_name/delegate_depth/max_depth/max_children`;
`tools/prime_runtime.py:203-221` builds the same). Not a defect.

### IN-05: Messaging error mislabeling — RESOLVED

**Evidence [source]:** `MessagingConnector.send/observe`
(`prime/messaging.py:119-140`) classify by cause in registry validation order:
empty body → `bad_value`; send failure without the members hint →
`unknown_sender`; with hint → `unknown_recipient`; observe error row →
`unknown_session`. (Note: empty-string bodies never reach the connector —
`require_str` rejects them as `bad_type` at decode; the connector's
`bad_value` branch covers whitespace/degenerate bodies that pass the gate.)

## New findings (AI reviewer)

### Warnings

#### WR-15: Whitespace-only strings pass the typed boundary and fail deeper as untyped errors — RESOLVED (fix verified)

**Resolution (verified 2026-10-09):** repaired as specified — strip-checks
in the decoders, shared `require_str` untouched — and re-verified end to
end with typed `code` envelopes, clean audits, untouched stores, preserved
optional-name/self-rename semantics, and a wider blank-shape sweep (see
Verification of WR-15 fix). The analysis below is retained as the historical
record of the defect.

**File:** `omega_prime/prime/goals.py:52-68` (decoder),
`omega_prime/agent/goals.py:107-111` (store rejection),
siblings in `omega_prime/agent/rlm.py:604-612` (`_admit`) and `:795-800` (`rename`)
**Flow [source + repro]:** the shared `require_str` (`prime/types.py:59-64`)
accepts any non-empty string, including `"   "`. Three typed decoders rely on
it without a blank check, while the capability layer strip-checks:
- `goal_set {"objective": "   ", "steps": ["x"]}` decodes cleanly
  (**[repro]** `SetGoalRequest.from_dict` returns `objective='   '`), then
  `PrimeGoalStore.replace_goal` raises bare `ValueError("objective must be a
  non-empty string")`. End-to-end through `ToolRegistry.dispatch` the model
  sees `{"error": "ValueError: objective must be a non-empty string"}` —
  **no `code` field** (**[repro]**), audited as
  `("goal_set", "error", "ValueError: …")` instead of a `<code>: <reason>`
  verdict. Atomicity holds (store still holds the previous objective —
  **[repro]**), so this is a contract defect, not data loss.
- `rlm_spawn {"prompt": "p", "name": "  "}` and the equivalent `rlm_rename`
  decode cleanly, then `_admit`/`rename` raise bare
  `TypeError("name must be a non-empty str")` (**[repro]**; zero files
  written — validation precedes registration/persist).
- Blank goal **steps** do not share the hole: the decoder strip-checks them
  (`bad_value`, pinned by test). Heartbeat `session` likewise strip-checks
  (`prime/heartbeat.py`, `bad_type`, pinned). The objective/name paths are
  the inconsistent remainder.
**Consumer effect:** a whitespace-only objective or child name contradicts the
"every malformed request is a typed `code: reason` error" boundary claim: audit
consumers keyed on `code` miss these, and the model gets an
implementation-flavored string. No test pins the whitespace-objective path
(verified: `test_prime_goal_surface.py` covers blank *steps* only).
**Fix:** mirror the existing heartbeat-session pattern at the three decoders,
not in shared `require_str` (whose other call sites — cell code, command args
— may legitimately carry whitespace):
```python
# prime/goals.py SetGoalRequest.from_dict, after require_str:
objective = require_str(payload, "objective", what="SetGoalRequest")
if not objective.strip():
    raise PrimeError("bad_value", "SetGoalRequest.objective must not be blank")
```
(same shape for `SpawnRequest.name` / `RenameRequest.name` with their `what`
tags). Add one registered-tool test per path asserting `bad_value`/`bad_type`
**with** a `code` field and an untouched store.

### Info

#### IN-06: Blank progress-note text is accepted and stored on the list channel — CONSCIOUSLY NOT CHANGED

**File:** `omega_prime/agent/rlm.py:846-870` (`progress_note`)
**Flow [source + repro]:** `progress_note` checks only `isinstance(str)` and the
512-UTF-16-unit cap — `"   "` is accepted (`{"accepted": true}`) and stored as
`child.progress_note`, hence visible in `rlm_list_subagents` (**[repro]**:
list row shows `'   '`). Same principal as IN-02 (parent writing its own
channel), no cross-boundary effect, no crash — informational. Per the fix brief this is a **conscious non-change**: the pinned Prime
contract (`tests/parity/rlm_progress_note.json`, source `prime-agent
`rlm/__init__.py`) bounds progress notes only by length (512 UTF-16 units)
and rate (10 s throttle) [receipt — stated in the fix brief; code side
confirmed: `ProgressNoteRequest` still decodes message via plain
`require_str` with no blank check]. A blank strip-check would diverge from
the pinned contract; left as-is by decision, not by oversight.

## Items checked and found sound (no finding)

- **Two-lock RLM design (task item a):** lock order persist-outer →
  registry-inner holds at every site; `_settle` takes persist only; `collect`
  waits on futures outside both locks; admission re-checks `deleting` under
  persist before submit (a child deleted mid-admission never starts and its
  tombstone is not clobbered); settle-vs-delete converges on tombstone-wins;
  `progress_note` throttle fields mutate under the registry lock;
  post-registration `_Child` reads outside the lock are benign stale reads.
  8-thread list/collect hammer ran clean **[repro]**.
- **Handler convention (task item b):** all 7 families call `reject_extra`
  first, never merge `**extra`, default required params to `None`, catch no
  `PrimeError` (grep-verified), declare every schema property in the handler
  signature, and keep result envelopes unchanged (bare entry/list passthroughs
  preserved; `harness_get` miss stays a domain `{"error": …}` audited
  `allowed`, as before).
- **Heartbeat/kernel decoding (task item c):** `_finite_number` rejects
  bool/non-number/non-finite and non-positive intervals; `due_at` finite;
  calendar overflow maps to `bad_value`; kernel `_decode` gates
  version/shape/unknown-fields before any import; all pinned-runtime imports
  (`factory_api`, `bash_api`, `skills`, `native`, `bound`) and kernel builds
  (`_kernel_for` mkdir) happen inside connector methods, i.e. strictly
  post-decode — a rejected request imports nothing and creates no files
  (pinned by `tmp_path.iterdir() == []` assertions across
  `test_prime_kernel_boundary.py`). **Empty heartbeat prompt is deliberately
  accepted** (`test_empty_prompt_and_explicit_due_at_are_accepted` pins it;
  the runtime only requires `isinstance(prompt, str)`) — checked, not a defect.
  `observe` without `mark_read` always marks read; the decoder still supports
  `mark_read=False` for direct callers — deliberate strictness, pinned by
  `test_loop_observe_rejects_undeclared_mark_read…`.
- **Loop argument edges (task item d):** `None`/`""` → `{}`; whitespace,
  truncated JSON, JSON scalars, and non-str/non-dict types → error rows;
  `RecursionError` (deeply nested) is caught alongside `ValueError`;
  duplicate keys resolve last-wins per stdlib (no custom handling needed);
  huge payloads parse normally and face per-field type checks. Refusal
  scoping reads the last tool round only, anchored on dispatcher-raised
  `error:` rows.
- **Goals atomicity (task item e):** objective/budget/steps all validated
  before either file write; steps replace (no inheritance); the returned
  status is post-write; the inter-write crash window is documented in the
  `replace_goal` docstring. The former WR-15 whitespace remainder is now closed (see Verification of
WR-15 fix); the inter-write crash window remains the only stated non-goal.
- **Assembler rules (task item f):** `--enable-family` requires `--output`,
  never writes/compares the canonical artifact; `--check` compares PATH;
  plain `--output` redirect round-trips bytes.
- **Test hygiene (task item g):** all boundary suites confine writes to
  `tmp_path` (asserted via `rglob`/`iterdir` emptiness and `elsewhere/`
  non-creation, plus `monkeypatch.chdir` where CWD matters); no `sleep`s or
  timing-sensitive waits (the `timeout_ms=5000` uses are caps over
  instantaneous scripted runners); error assertions use prefix/substring
  matching (`startswith("error:")`, `"unknown_field" in …`,
  `reason.startswith(…)`) rather than brittle exact wording; every defect
  class under test fails closed (a broken fix would fail the assertion,
  verified by reading the assertions against the corrected code paths, not
  by mutation runs).
- **Kernel host strictness fallout:** `InProcessHost` constructs
  `RlmHost(parent)` directly (`prime_kernel/host.py:53`), so the new
  `require_parent` applies to kernel embedders too — all construction sites
  (`tools/prime_runtime.py:203-221`, kernel test fixtures) already carry the
  full five-field contract. No breakage found.
- **Rename `target: null` → self-rename:** matches the pinned host contract
  (`rename` treats `None` as self, same as `NoRlmHost`); schema requires
  `target`, so only an explicit null reaches it. Contract-consistent, not a defect.

## Reproduction log (throwaway scripts, not committed)

All under `/tmp/p61repro/`, run with the repo venv; test suites were **not** run.

- `r1.py` — `SetGoalRequest` decode edges: whitespace objective decodes
  (hole), `token_budget=0` → `bad_value`, `token_budget=True` → `bad_type`.
- `r2/r4.py` — end-to-end whitespace `goal_set` through `ToolRegistry.dispatch`
  with real grants: untyped `ValueError` envelope without `code`, generic audit
  reason, store untouched. (First attempt without grants correctly showed
  approval denial — ordering evidence.)
- `r3.py` — 13 `_arguments` shapes: only `None`/`""`/valid-object/dict pass;
  all others are non-executing problems.
- `r5.py` — heartbeat/kernel/collect edges: blank session/NaN/Inf/bool
  rejected typed; empty prompt accepted (pinned deliberate); empty
  cell/bash rejected; empty goal-command args accepted (status query);
  negative/bool timeouts rejected; huge timeout accepted (deliberate per IN-03).
- `r6.py` — blank RLM spawn/rename names → untyped `TypeError`, zero files.
- `r7.py` — blank progress note accepted and listed; 8-thread
  list/collect hammer: zero errors.
- `r4.py`/`r6.py` re-run post-fix: whitespace objective → `bad_value`
  with `code`, audited `bad_value: …`, store untouched; blank spawn/rename
  names → `bad_value` with `code`, zero files.
- `r8.py` (post-fix) — optionality preserved: omitted/`null`
  create-session name still admitted (auto-named); blank name →
  `bad_value`; rename `target: null` still decodes to self-rename.

## Verification of WR-15 fix (2026-10-09)

**Scope:** the two repaired source locations, the three new tests, a sweep for
uncleared siblings, and re-runs of the original repros. Read-only except this
report; no suites, linters, or builds run.

- **Fix confirmed [source]:** `SetGoalRequest.from_dict`
  (`prime/goals.py`) rejects a blank objective as `bad_value` after
  `require_str`, before any store touch. `SpawnRequest.name` rejects blank via
  `_nonblank_name`; `CreateSessionRequest.name` via `_optional_name`
  (`None`/absent still allowed, blank rejected); `RenameRequest.name` via
  `_nonblank_name` with the `target: null` → self-rename path untouched
  (`prime/rlm.py`: `_check_selector` additionally hardens blank string/dict-row
  selectors). Shared `require_str` (`prime/types.py:59-63`) verified untouched.
- **Semantics preserved [repro, `r8.py`]:** omitted/`null` create-session name
  still admitted (auto-named `rlm-session-*`); `RenameRequest(target=None)`
  still decodes to the self-rename target.
- **End-to-end re-verified [repro, re-ran `r4.py`/`r6.py`]:** whitespace
  `goal_set` → `{"error": "bad_value: …must not be blank", "code":
  "bad_value", …}`, audited `("goal_set", "error", "bad_value: …")`, store
  still holds the previous objective; blank spawn/rename names → `bad_value`
  with `code`, zero files written.
- **New tests read [source]:** `test_blank_objective_is_rejected_and_the_stored_goal_is_untouched`
  and `test_blank_objective_on_a_fresh_store_writes_nothing`
  (`test_prime_goal_surface.py`) assert `code == "bad_value"`, byte-identical
  goal files, and a readable seeded goal; `test_blank_names_are_typed_bad_value_and_create_nothing`
  (`test_prime_rlm_surface.py`) settles a real child first, then asserts
  `bad_value` + audit-`error` for all three blank-name tools with no new
  documents, rows, or roster changes. All fail closed on the defect.
- **Sibling sweep (no new defect):** harness store validation is falsy-based,
  not strip-based (`learning/harness.py`), so blank harness ids/titles are
  stored as-is with no untyped rejection — no WR-15-shaped hole; `refine()`
  performs no blank-trigger rejection; heartbeat `clear` returns a result dict
  on unknown ids (domain envelope, not an exception); blank send recipients /
  observe sessions map to typed `unknown_recipient` / `unknown_session`;
  blank spawn prompts and kernel run-ids have no downstream blank rejection
  anywhere in the chain (accepted-as-asked, no envelope violation). Blank
  progress-note message remains accepted per the conscious IN-06 decision.
- **Accounting:** this pass raised 2 findings (WR-15 warning, IN-06 info);
  **0 remain open** (WR-15 resolved by the verified fix, IN-06 closed as a
  conscious non-change). No new defects found during verification.

## Gate limitations kept distinct (not accepted by this review)

LOOP-07 literal full unmodified historical suite, REPO-04 source-only Cargo
resolution, and DONE-01/02 lifecycle (audit acceptance, archive/cleanup,
ownership-safe publication) remain open and are outside this source review.

---

_Reviewed: 2026-10-09T18:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
_Pre-repair report: `.planning/phases/61-prime-loop-gap-closure/61-REVIEW-pre-repair.md`_
_Verification of WR-15 fix: 2026-10-09 — WR-15 RESOLVED, IN-06 conscious non-change, no new defects._
