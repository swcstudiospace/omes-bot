---
phase: 61-prime-loop-gap-closure
reviewed: 2026-10-09T00:00:00Z
depth: deep
files_reviewed: 25
files_reviewed_list:
  - omega_prime/prime/types.py
  - omega_prime/prime/errors.py
  - omega_prime/prime/rlm.py
  - omega_prime/prime/harness.py
  - omega_prime/prime/goals.py
  - omega_prime/prime/autonomous.py
  - omega_prime/prime/messaging.py
  - omega_prime/tools/rlm.py
  - omega_prime/tools/harness.py
  - omega_prime/tools/goals.py
  - omega_prime/tools/autonomous.py
  - omega_prime/tools/agent_message.py
  - omega_prime/tools/registry.py
  - omega_prime/agent/rlm.py
  - omega_prime/agent/prime_hooks.py
  - omega_prime/agent/conversation_loop.py
  - omega_prime/agent/runtime.py
  - omega_prime/prime_kernel/host.py
  - omega_prime/assemble.py
  - omega_prime/tooling/catalog.py
  - omega_prime/tests/test_prime_contracts.py
  - omega_prime/tests/test_prime_failure_injection.py
  - omega_prime/tests/test_rlm.py
  - omega_prime/tests/test_prime_regression.py
  - omega_prime/tests/test_shell.py
findings:
  critical: 2
  warning: 14
  info: 5
  total: 21
status: issues_found
---

# Phase 61: Current Cross-Gap Code Review (existing-v10 repair)

**Reviewed:** 2026-10-09
**Depth:** deep (cross-file; read-only; no tests, builds, linters or formatters were run: `checks_run = []`)
**Status:** issues_found

Historical narrow review (14 findings, CR-01/WR-0x/HB-0x) is preserved unchanged at
`local://phase61-review-before-current.md`. This report is a separate, current review of the
cross-gap repair and does not re-open those dispositions.

## Scope and method

Explicit file scope is the `files_reviewed_list` above. Also read for tracing only:
`agent/turn_tool_round.py`, `agent/degraded.py`, `agent/goals.py`, `agent/autonomous.py`,
`agent/messaging.py`, `learning/goals.py`, `session/persist.py`, `tools/prime_runtime.py`,
`mcp_server.py`, `scripts/assemble-prompts.sh`, plans `61-03/04/05/06-PLAN.md`, the shared contract,
and `61-EVIDENCE.json` (smoke script bodies). No LSP server is exposed in this harness; reference
tracing was done with `grep` over `omega_prime/`, `docs/`, `README.md`.

Evidence classes are kept separate below: **[source]** = verified in current source,
**[receipt]** = from the supplied `61-EVIDENCE.json`/contract, **[inference]** = reasoning not exercised.

Not claimed by this report: a signed A09 security verdict, closure of all 32 criteria, cloud CI,
a native auto-engine/daemon, or a fully green old suite.

## Summary

The typed/versioned connector cutover, the policy-then-approval-then-decode ordering in
`ToolRegistry.dispatch`, the lease/cap/precedence structure of the loop boundary, and the durable
terminal-settlement barrier (`settled_on_disk` + persist lock + tombstone-wins) are sound for the
paths the receipts exercised. The review found two blockers that defeat the "strict decode before
effects" and "bound identity" claims through paths the receipts and permanent tests do not
exercise, and a set of warnings in durable RLM recovery, `goal_set`, the audit trail, catalog/prompt
assembly and test coverage.

## Critical Issues

### CR-01: Messaging handlers let model-supplied `**extra` override the session-bound identity (sender spoof, cross-session inbox read/consume)

**File:** `omega_prime/tools/agent_message.py:67-96` (payload dict at 74-82 and 90-95)
**Flow [source]:** `agent_message_send` builds
`{"sender": session, "recipient": ..., "body": ..., "schema_version": ..., **extra}`;
`agent_observe` builds `{"session": session, "schema_version": ..., **extra}`. `**extra` is spread
**last**, so a duplicate key wins. `registry._call` (`tools/registry.py:205-212`) calls any handler
that has `**kwargs` as `handler(**arguments)` with the raw model arguments, and `sender`, `session`
and `mark_read` are all members of `_SEND_FIELDS` / `_OBSERVE_FIELDS` (`prime/messaging.py:30-31`),
so `reject_unknown` accepts them. The comment at `tools/agent_message.py:64-66`
("The sender is this session's bound name, never a caller-supplied field") is therefore false.
**Consumer effect:**
`agent_observe {"session":"other"}` returns another registered session's inbox and (default
`mark_read=True`) marks it read, so the rightful recipient never sees it; `agent_observe` is **not**
approval-gated (`_WRITE_TOOLS = {"agent_message_send"}`). `agent_message_send {"sender":"other",...}`
delivers a message that the recipient sees as coming from `other`. The shared per-process registry
(`_shared_registry`, line 33) makes every session in the process reachable. This is a session
isolation break reachable by any tool-calling model output (including prompt-injected content).
The connector error path also maps every registry error to `unknown_recipient` (see IN-05).
**Fix:** bound fields must not be overridable. Reject rather than silently overwrite:
```python
_BOUND = {"sender"}  # observe: {"session"}
clash = _BOUND & extra.keys()
if clash:
    return PrimeError("unknown_field", f"{', '.join(sorted(clash))} is bound to this session").to_dict()
payload = {**extra, "sender": session, "recipient": recipient, "body": body, "schema_version": schema_version}
```
(same for `session` in `agent_observe`). Add a consumer test: a registry with two sessions;
`agent_observe {"session": "<other>"}` and `agent_message_send {"sender": "<other>"}` must return
`unknown_field` and leave the other inbox unread.

### CR-02: The conversation loop turns unparseable tool-call arguments into `{}` and executes the tool, so the strict request decoders are never reached for no-required-argument write tools

**File:** `omega_prime/agent/turn_tool_round.py:85-96` (`_arguments`) and `:99-107` (`_execute`); consumed via `omega_prime/agent/runtime.py:30-37` (`_dispatcher`)
**Flow [source]:** `_arguments` returns `{}` when `json.loads` raises (`JSONDecodeError`) or the parsed
value is not an object. `_execute` then runs `_call_without_args(fn)` for the empty dict. The
dispatcher calls `registry.dispatch(name, {})`; policy and name-level approval pass (approval is
`_has_approval(log, name)` only, `tools/registry.py:92-96,170-177`), and the handler runs with
defaults. No error row is produced and no typed `bad_type` ever reaches the model.
**Consumer effect:** a truncated/garbled argument string (a normal result of an output cut-off) for an
already-approved write tool executes it with defaults instead of failing: `goal_clear`, `goal_pause`,
`goal_resume`, `autonomous_stop`, `harness_rollback` (restores the previous harness snapshot),
`autonomous_start` (starts with config defaults rather than the intended bounds), `rlm_collect` (all
children). This is data-loss/incorrect-behavior risk on exactly the plan's "malformed request has no
side effect" boundary (T61-INT-TYPE). The receipts' malformed cases all send well-formed JSON with a
bad field (`model: true`, `gate: "make test"`), so they do not cover it. The lines are pre-existing
(`turn_tool_round.py` is not in the changed-file list) but this is the live path through which the
plan's claim must hold.
**Fix:** make an unparseable or non-object argument payload an error row, not an empty call:
```python
def _arguments(raw):
    ...
    if isinstance(raw, str):
        try: parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"arguments are not valid JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be a JSON object")
        return parsed
```
and have `_split_call`/`_execute` convert it to `error: ...` for that call only. Add one loop-level test:
a scripted model emits `{"global_": true` for `harness_rollback`; assert the row starts with `error:`
and the stored snapshot is unchanged.

## Warnings

### WR-01: Omitted required arguments never reach the typed decoders; the model sees a Python `TypeError`

**File:** `omega_prime/tools/rlm.py:62-70,93-99,109,119-127,152-159`; same shape in `tools/harness.py:78-95`, `tools/goals.py:70-84`, `tools/agent_message.py:67-72`
**Flow [source]:** every handler declares required positional parameters **and** `**extra`.
`registry._call` takes the `VAR_KEYWORD` branch (`handler(**arguments)`, `registry.py:204-206`), so
the registry's own "missing required arguments" check is skipped and Python raises
`TypeError: rlm_spawn() missing 2 required positional arguments: 'prompt' and 'name'`.
`registry.dispatch` returns `{"error": "TypeError: ..."}` with no `code`.
**Consumer effect:** `rlm_spawn {}`, `rlm_delete_subagent {}`, `rlm_progress_note {}`, `rlm_rename {}`,
`goal_set {}`, `harness_upsert {}`, `agent_message_send {}` yield an implementation-flavored generic error,
not `bad_type`, contradicting the comment at `tools/rlm.py:60-69` ("never ... a generic registry TypeError")
and the plan task 2 (structured codes). No side effect occurs, so this is a contract/robustness defect.
**Fix:** give required parameters a `None` default in the handler signatures (`prompt: Any = None`) and let
`require_str` raise `bad_type`; add one registered-tool test per family that omits a required field.

### WR-02: Handlers swallow `PrimeError` and return its dict, so the audit trail and tracer record malformed/rejected calls as `allowed`

**File:** `omega_prime/tools/rlm.py:88,107,114,125,150,169,188`; `harness.py:98,119,139,160,183,200`; `goals.py:86-122`; `autonomous.py:104,116,124`; `agent_message.py:83,96`; versus `tools/registry.py:106-113`
**Flow [source]:** `registry.dispatch` has a dedicated `except PrimeError` branch that records `verdict="error"`
with `code: reason`, but every handler catches `PrimeError` first and **returns** `exc.to_dict()`. The
registry then falls through to `self._record(name, "allowed")` (`registry.py:124/131`). Meanwhile
`_dispatcher` (`runtime.py:30-37`) sees the `error` key and raises, so the transcript shows a failed
call.
**Consumer effect:** audit (`_audit.append`) and tracer spans say `allowed` for calls the loop treats as
errors (version/unknown-field/type rejections). The "typed decoding precedes capability effects, not
authorization" evidence cannot be reconstructed from the audit log, and any consumer keyed on audit
verdict (policy review, tracer dashboards) is misled.
**Fix:** delete the per-handler `try/except PrimeError` and let `registry.dispatch` convert it (that branch
already returns the same `exc.to_dict()` envelope). Verify with one test asserting an audit record with
`verdict == "error"` and reason `unsupported_schema_version: ...`.

### WR-03: Undeclared `scope` (and other decoder-allowed fields) bypass the explicit `global_` bool guard

**File:** `omega_prime/tools/harness.py:85-96,109-117,130-137,150-158,172-181,192-198`; `tools/goals.py:76-84`
**Flow [source]:** the payload is `{..., "scope": _scope(global_), ..., **extra}` with `extra` last. `scope`
is an allowed decoder field (`prime/harness.py:42-47`) but is not in any tool schema, so a call with
`{"scope": "global"}` (or `global_: false, scope: "global"`) is accepted and `scope` silently overrides the
type-checked `global_` mapping. `_scope`'s docstring promises "never a truthy coercion into the
cross-session store". The same mechanism lets `goal_set` take `stale_after_turns` (decoder field, not in
the schema).
**Consumer effect:** a model can write/delete/refine/rollback the cross-session **global** harness store
via an undeclared alias that the schema and documentation never expose; contradictory `global_`/`scope`
inputs resolve to the more privileged scope with no error.
**Fix:** reject keys that duplicate a tool-bound parameter (same change as CR-01), and drop `scope`/
`stale_after_turns` from the decoder's accepted tool-surface or expose them in the schema deliberately.

### WR-04: `goal_set` is not atomic, the strict decode misses the store's step invariant, and the response/steps are stale

**File:** `omega_prime/prime/goals.py:47-69,202-209`
**Flow [source]:** `SetGoalRequest.from_dict` accepts any list of `str` (including `""`/`"  "`). `GoalsConnector.set_goal`
first calls `store.set_objective(...)` (rewrites the base objective and resets the sidecar to `active`, `tokens_used=0`)
and only then `store.add_step(step)` per step; `GoalStore.add_step` raises `ValueError` on blank text
(`learning/goals.py:36-42`). `{"objective":"new","steps":["a"," "]}` leaves the new objective active with a
partial step list while the tool returns `ValueError: step must be a non-empty string`.
Two further consequences of the same function: (1) `result` is captured **before** the steps are added, so the
returned status never contains the new steps; (2) base `set_objective` does not clear existing steps, so replacing a
goal inherits the previous goal's unfinished steps, and `continuation_prompt` then steers to "Next step: <old step>".
(2) and the stale return predate this phase; the typed-decode partial effect is what the plan's T61-INT-TYPE
forbids.
**Fix:** validate steps (`text.strip()`) in `SetGoalRequest.from_dict`; in `set_goal` call `store.clear()` semantic
for steps before adding (or add a store method that replaces objective and steps in one `_save`) and return
`store.prime_status()` after the last step. Cover with a registered-tool test: blank step -> `bad_value`, goal unchanged.

### WR-05: `max_minutes` accepts `NaN`/`Infinity`, silently disabling the time limit

**File:** `omega_prime/prime/autonomous.py:79-90`; consumed in `omega_prime/agent/autonomous.py` budget check (`elapsed_minutes >= budget.max_minutes`)
**Flow [source]:** `json.loads` (used by the tool-call path) accepts `NaN`/`Infinity`; `nan <= 0` is False and
`isinstance(nan, float)`, so the decoder passes. `elapsed >= nan` is never true, so the "bounded" run has no time
bound; the `autonomous_start` result then serializes `"max_minutes": NaN` (not valid strict JSON).
**Fix:** reject `not math.isfinite(max_minutes)` in `StartRequest.from_dict` (`bad_value`).

### WR-06: RLM host parent contract is implicit and does not match a real `Agent`; receipts used a `SimpleNamespace` shim

**File:** `omega_prime/agent/rlm.py:274-277,512-523`; `omega_prime/agent/conversation_loop.py:112-114` (Agent fields)
**Flow [source]:** `RlmHost` reads `parent.session_dir`, `parent.depth`, `parent.max_depth`, `parent.max_children`,
`parent.session_name` via `getattr` with defaults. `Agent` (and `OmegaPrimeAgent`) defines `delegate_depth`, `max_depth=2`,
`max_children=1`, `session_name="default"` and **no** `session_dir` or `depth`. `tests/test_growth.py:613-617` registers the
family with a real `Agent` as parent. For that parent: durable files go to the process working directory
(`getattr(..., "session_dir", ".") or "."` -> `./sessions/<id>.json`, `./rlm-children/<id>`), `depth` is always 0 so
`RLM depth limit reached` can never fire (a child that registers the family on its own `Agent` restarts at depth 0), only
one child may exist, and `session_name="default"` is the ownership key shared by every default-named agent in that CWD.
**[receipt]** the `cross_gap_actual_typed_loop_smoke` script builds the RLM parent as
`SimpleNamespace(session_dir=..., session_name="owner", depth=0, max_depth=2, max_children=4)`; permanent
tests use `_Parent` stubs the same way. The real-Agent-as-parent composition is untested.
**Fix:** make the parent contract explicit (a small `Protocol`/constructor args: `session_dir`, `depth`, `session_name`
required; read `delegate_depth`), fail construction when missing instead of defaulting to `"."`, and add one test with a
real `OmegaPrimeAgent` parent asserting durable files land in the configured directory and the depth bound fires.

### WR-07: `rlm_create_session` – `cwd` is misleading and breaks recovery; roster record is created before admission

**File:** `omega_prime/agent/rlm.py:274-277,757-814` (create_session at 757; `session_store.create` at 778-781; `_spawn_impl` at 491)
**Flow [source]:** (a) `cwd` only selects the directory of the durable JSON (`_durable_dir(cwd)` -> `save_session(root, ...)`). It is not
passed to the child runner (`_run_child(prompt, model=, thinking=)`), although the tool schema documents
"Optional working directory" (`tools/rlm.py` schema). A model-chosen `cwd` is an unvalidated path (relative values resolve against the
process CWD) under which `sessions/<id>.json` is created. (b) `recover_all()` scans only `_durable_dir()` (no cwd), so a session created
with a `cwd` is not recovered by a fresh host although the tool is described as creating a session "that survives this turn".
(c) `session_store.create(...)` runs **before** `_spawn_impl`, which raises on duplicate name, child/depth limit or a failed first
persist; the roster record is then orphaned and never removed.
**Consumer effect:** the model believes the child ran in `cwd`; restart silently loses the session; failed creates leave phantom roster rows.
**Fix:** either wire `cwd` into the child runner or drop it from the schema/decoder; store recovery roots durably (scan the default root only and
reject `cwd` here); call `session_store.create` after `_spawn_impl` succeeds (and delete it if the later step fails).

### WR-08: Recovery rewrites already-terminal records on every host construction; one write failure disables the whole RLM family

**File:** `omega_prime/agent/rlm.py:257-270,322-412,404-410,414-446`
**Flow [source]:** `RlmHost.__init__` calls `recover_all()`, which calls `recover_session()`, which unconditionally calls `_persist_child(...)`
for every owned record (including `completed`/`error` documents that need no change). `host_for` assigns `parent._rlm_host` only after the
constructor returns, so an `OSError` (read-only or full session directory, permissions) from that write propagates out of
`connector()` on **every** RLM tool call (`rlm_list_subagents`, `rlm_collect`, `rlm_delete_subagent`, ...) until the directory is writable.
`_read` converts read errors to `ValueError` and those are skipped (good), but write errors are not.
Ownership is only `session_name` (`_owner_name`), and an interrupted ("running") record belonging to another **live** host in the same directory
with the same name is rewritten to `error: interrupted ... not replayed`.
**Fix:** write during recovery only when the status actually changes (`running` -> `error`); treat a failed recovery write as a per-record warning
(keep the record in memory as an error) rather than failing host construction; document/guard the one-live-host-per-owner assumption.

### WR-09: Deleted-child tombstones retain the full prompt and answer on disk and are never reaped

**File:** `omega_prime/agent/rlm.py:283-319` (messages built at 297-299 regardless of `deleting`), `:660-690`
**Flow [source]:** `_persist_child` always writes `messages = [user prompt, assistant answer]`; the tombstone (`status="deleted"`) is therefore the
same document with the status flipped. `delete_subagent` removes the in-memory row but no code deletes the file. The delete tool description says
"Reap one direct RLM child and drop its retained result."
**Consumer effect:** after `rlm_delete_subagent` the child's private answer remains in `sessions/<id>.json` (readable through any file tool),
contradicting the privacy intent of RLM-04 for delete.
**Fix:** write the tombstone with `messages=[]` (or only identity/status) and metadata `error=None`; keep the tombstone only to defeat resurrection.

### WR-10: `collect` can return `answer_preview`/`error` on a child that it reports as `running`

**File:** `omega_prime/agent/rlm.py:218-241` (`to_result`), `:553-580` (`_settle`)
**Flow [source]:** `_settle` assigns `child.answer`/`child.error` before the persist, but `to_result` reports `status="running", settled=False` until
`settled_on_disk` is set while still populating `answer_preview=self.answer_preview()` and `error=self.error`. A concurrent `rlm_collect` during the
persist window therefore sees result text on a "running" row; if the persist then fails, the already-visible answer sits next to a later
`durable save failed` error.
**Fix:** in `to_result`, set `answer_preview`/`error` to `None` unless `done`; (or publish answer/error only after persistence).

### WR-11: Child registry is mutated and iterated without synchronization; delete can race an in-progress spawn

**File:** `omega_prime/agent/rlm.py:508-552` (`_spawn_impl` registers at 541, submits at 548), `:637-662,660-690`
**Flow [source]:** `_children` is a plain dict. `spawn`, `delete_subagent`, `recover_session` mutate it; `list_subagents`, `_select`, `rename` iterate it,
and child worker threads reach `list_subagents`/`progress_note` through the kernel host. Only persist writes take `_persist_lock`. Name-uniqueness and
child-limit checks in `_spawn_impl` are check-then-act. Separately, `delete_subagent` between the first persist (543) and `child.future = future` (549)
sees `future is None`, writes the tombstone and removes the child, and `_spawn_impl` then still submits the worker: a deleted child runs its prompt.
**[inference]** tool rounds are sequential, so the dominant exposure is the kernel/child-thread path; not exercised by receipts.
**Fix:** take `_persist_lock` (it is an `RLock`) around registry reads/mutations and re-check `child.deleting` just before `submit`.

### WR-12: `_refusal_reason` marks the whole public run terminal for any earlier approval/policy refusal, even when the model recovered

**File:** `omega_prime/agent/conversation_loop.py:461-476`, used at `:647-653,658-708`
**Flow [source]:** the scan covers `messages[turn_begin:]` (every tool row of the public run, including earlier continuation rounds) and matches the
substrings `policy forbids` / `approval required` in any `error:` row. If a tool was refused once and the model then completes the work another way,
the final boundary is `terminal=True`: `turn_result["completed"]=False`, the driver is charged as incomplete (no gate, and under the sticky stop semantics
documented in the historical review it stops until `autonomous_start`), goal continuation is vetoed, and `turn_exit_reason` is `approval_refused`.
**Consumer effect:** one recovered refusal permanently demotes an otherwise finished turn and halts autonomous continuation.
**Fix:** scope the scan to the most recent tool round (rows after the last `assistant` message with `tool_calls`) or to refusals not followed by a
successful row for the same tool; keep the honest terminal reason only when the final answer immediately follows the refusal. This is a semantics decision
for the parent; if the broad scope is intended, say so in the contract and document that recovery does not clear it.

### WR-13: `assemble-prompts --enable-family` overwrites the committed canonical default-off artifact; the enabled path has no production consumer

**File:** `omega_prime/assemble.py:198-257` (write at 257); `scripts/assemble-prompts.sh` forwards `"$@"`
**Flow [source]:** without `--check`, `main` always writes `prompts-assembled/OMEGA_PRIME.xml`, including when `--enable-family` produced a non-default
text. A subsequent `--check`/`setup_check` (default-off) then fails against it until regenerated. The only non-test callers of `render` are the default
assembly and `setup_check`; `mcp_server` registers enabled families (harness/goals/heartbeat/autonomous/kernel) but nothing renders the matching enabled
prompt, so the enabled-family prompt is reachable only by a manual CLI flag.
**Consumer effect:** a user enabling a family and regenerating clobbers the canonical artifact; the prompt a host loads does not describe the tools
the server offers (INT-04 enabled half is only exercised by `render(...)` in `test_shell.py`).
**Fix:** write enabled-family output to an explicit `--output` path (refuse to overwrite the canonical file when any `--enable-family` is passed) and decide
which runtime consumer renders the effective prompt. **[receipt]** the supplied surface smoke covers default-off bytes only.

### WR-14: Permanent-test gaps and non-consumer fixtures leave the above defects undetected

**Files:** `omega_prime/tests/test_prime_failure_injection.py`, `test_prime_regression.py`, `test_rlm.py`, `test_prime_contracts.py`
**Evidence [source]:**
- No test asserts bound-identity for messaging (CR-01), malformed/truncated argument JSON in the loop (CR-02), required-field omission (WR-01),
  audit verdicts for typed errors (WR-02), the `scope` alias (WR-03), blank goal steps (WR-04) or NaN budgets (WR-05).
- No test proves policy (`ToolRegistry(policy=...)`) and approval precede decode with a malformed payload (the ordering is correct in `registry.py:89-117`
  but unpinned by any consumer test).
- `test_prime_regression.py:39-45` builds a test-local `dispatcher` that returns the raw JSON string, not `OmegaPrimeAgent._dispatcher`
  (`runtime.py:30-37`), so denial/failed rows differ from the production consumer (`error: ...`); the pre-v10 parity claim covers `Agent` + registry,
  not the registered public agent.
- RLM tests and the receipt smokes use stub parents (`_Parent`, `SimpleNamespace`), never a real `Agent` parent (WR-06).
- `test_rlm.py:620` monkeypatches the private `host._persist_child`; the contract accepts two deterministic durable races, but this one pins an internal
  method name. Prefer the `rlm_module.save_session` seam already used at `:586,:661`.
**Fix:** add the small consumer tests named in each finding; point the regression fixture at `OmegaPrimeAgent` for the error-row cases.

## Info

### IN-01: Dead exported preview field and defensive scrubbing; collect exposes only 200 characters
**File:** `omega_prime/agent/rlm.py:97,210`; `omega_prime/prime_kernel/host.py:27-33`; `omega_prime/agent/rlm.py:192-195`
`RLMSubagent.answer_preview` is always `None` now and `_metadata_snapshot` pops keys the typed view can no longer emit. Remove the field and the
pops (callers: `grep answer_preview`). Separately the only parent-visible answer channel truncates to `answer[:200]`; the full answer is only in the
JSON file. Confirm that is the intended Prime semantic.

### IN-02: Registered `rlm_progress_note` lets the root model write any child's progress note and consume its throttle window
**File:** `omega_prime/tools/rlm.py:154-166`; contrast `omega_prime/prime_kernel/host.py:253-262` (kernel path is child-bound)
Documented as an explicit-id contract in `host.py`; the effect is that the parent can forge the `progress_note` shown in `rlm_list_subagents` and block the real
child's next note for ~10 s. Same principal, so informational unless child-authored progress is meant to be trustworthy.

### IN-03: Version and wait bounds not enforced
**File:** `omega_prime/prime/types.py:20-30`; `omega_prime/agent/rlm.py:604-631`
`schema_version` 0/negative is accepted (only `> own` is rejected). `rlm_collect timeout_ms` has no upper bound and the wait does not observe the agent
interrupt flag, so a stuck child with a huge timeout holds the session lease.

### IN-04: Kernel host patches `rlm.repl` process-globally; the cached kernel pins the first `run_child`
**File:** `omega_prime/prime_kernel/host.py:68-83`; `omega_prime/tools/prime_runtime.py:150-170`
`install()` replaces module-level callables; two roots in one process route cells to whichever host installed last, and `_KERNELS[key]` ignores a later
`run_child`. **[inference]** only multi-root embedders are affected.

### IN-05: Messaging connector labels every registry failure `unknown_recipient`
**File:** `omega_prime/prime/messaging.py:117-120`
Empty body or unknown sender also raise `PrimeError("unknown_recipient", ...)`, and the `members` hint from the registry is dropped. Map by cause (`bad_value`,
`unknown_sender`, `unknown_recipient`).

## Items checked and found sound (no finding)

- Order in `ToolRegistry.dispatch`: unknown tool -> policy -> approval -> argument parse/handler (`registry.py:89-117`); no decode before authorization.
- Optional `schema_version=None` is treated as absent; future version and unknown fields are strict typed errors in every request decoder.
- Native selector handling: `InProcessHost._resolve_model` never invents a model; `find_models` advertises none (`prime_kernel/host.py:121-136,293-300`).
- Terminal settlement: a late `_settle` persist cannot overwrite a tombstone (`deleted` is evaluated inside `_persist_lock`, `rlm.py:304`); a failed tombstone write rolls
  `deleting` back; `done` is not claimed before `settled_on_disk`; interrupted records recover as explicit errors with no replay.
- Loop: accounting is separate from continuation permission, provider exceptions propagate with usage already charged, and `guarded_hook` never wraps provider errors.
- Catalog: `full_inventory_registry` registers real definitions without dispatching handlers; `register_rlm_tools(registry, None)` constructs no host.
  Cold-import: lazy `PrimeError`/`GoalStatusView` imports in `registry.py`/`prime_hooks.py` break the observed cycle without removing exports.

## Gate limitations kept distinct (not accepted by this review)

LOOP-07 literal full unmodified historical suite (observed 376 passed / 2 failed incidental pins), REPO-04 source-only Cargo resolution (exit 101, user
packaging decision pending), and DONE-01/02 lifecycle (audit acceptance, archive/cleanup, ownership-safe publication) remain open and are outside this
source review. Retained upstream Rust diagnostics (5089 passed / 2 failed) were not rerun.

---

_Reviewed: 2026-10-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
