# Phase 55: RLM recursion port - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous

<domain>
## Phase Boundary

Port Prime's RLM recursion surface into Omega Prime as a rostered tool
family on top of the existing delegate machinery: spawn / collect /
list_subagents / delete_subagent / create_session / progress_note /
rename, with Prime's exact handle shapes, status vocabularies, selector
semantics, throttle rules, and no-host degraded behavior. In scope:
`omega_prime/agent/rlm.py`, `omega_prime/tools/rlm.py`, roster +
registration wiring, tests. Out of scope: the continual harness (Phase
56), factory workflows (later), the NDJSON kernel protocol (no second
process exists), true async concurrency model changes.

</domain>

<decisions>
## Implementation Decisions

1. **In-process concurrency via the existing patterns.** Omega Prime's
   loop is synchronous; Prime's spawn is concurrent. The port runs each
   spawned child on a `ThreadPoolExecutor` (the `agent/harness.py`
   speculative-execution precedent) with its own `Agent` + tool map (the
   `delegate.py` isolation precedent: child gets a new dict, parent never
   edited). `collect(timeout_ms)` waits on futures; timeout returns
   snapshots, never an error, never steers the parent.
2. **Exact wire vocabulary, Python-native transport.** Field names, status
   sets, and error strings match the Rust/Python sources verbatim (below)
   so future parity fixtures can diff behavior. The transport is direct
   in-process calls, not NDJSON frames.
3. **Degraded = truthful empties + explicit errors** (the
   `NoRlmChildren` contract): with the RLM family disabled, the tools are
   not registered at all (LOOP-05); an in-code call hits the same error
   strings Prime's no-host path returns.
4. **State:** per-parent-session child registry in-process; child results
   retained until delete; `create_session` persists through
   `session/persist.py` so a created session is resumable.
5. **Delegate untouched.** `delegate_task`/`join_delegate` keep their
   behavior; RLM tools are a new family beside them.

### The contract being ported (from source)

Kernel API (`prime-agent-runtime/src/rlm/__init__.py`):
- `spawn(prompt, *, name, model=None, thinking=None) -> RLMSpawnHandle(rlm_child_id, name, session_dir, model)`; name required + unique among siblings; wire type `"rlm.run"`.
- `collect(targets=None, *, timeout_ms=0) -> list[RLMChildResult]`; targets = handle | subagent row | name str | mixed list; None/empty = all direct children not being deleted; timeout>0 blocks only this call, returns current snapshots on elapse, never errors; completed children keep results until deleted.
- `list_subagents() -> list[RLMSubagent]`; status ∈ {running, completed, error}; activity.kind ∈ {waiting, writing, executing}.
- `delete_subagent(target)`; `create_session(prompt, name, model, thinking, cwd)` (depth-0 only); `progress_note(message)` — ≤512 UTF-16 code units, ~1/10s throttle, throttled ⇒ `accepted=False` + `retry_after_ms`, never raises; `find_models(query, limit=8)`.
- Collect status ∈ {queued, running, done, error, cancelled}; `settled: bool`.
- Decode discipline: every payload field type-checked; bool/int confusion rejected; host `{status: ok|error}` envelope; error ⇒ RuntimeError(message).

Host contract (`pa-core/src/session_engine/rlm_host.rs`):
- `RlmSubagentHost` trait: spawn / create_session / list_subagents / delete_subagent / collect / rename (rename self or one direct child; self-rename lands locally even with no host).
- No-host behavior (`NoRlmChildren`, lines 194-241): spawn ⇒ "rlm.spawn requires a daemon-backed session: this session has no RLM child runtime"; create_session ⇒ "rlm.create_session requires a daemon-backed depth-0 session"; list ⇒ empty; delete ⇒ `No direct RLM subagent matches "<target>" in the current parent session`; collect with targets ⇒ error naming first target, empty targets ⇒ empty list.
- `RlmSpawnRequest` carries `spawned_by_request_id` (the in-flight turn the spawn anchors to) and `cell_source_code` — the port records the spawning tool-call id analogously.

</decisions>

<code_context>
## Existing Code Insights

- `omega_prime/agent/delegate.py` (163 lines): isolation pattern (new
  tool-map dict per child, `child_tool_hook`, `child_model`,
  depth/children caps), `_PENDING` handle registry, `join_delegate`
  run-once semantics.
- `omega_prime/agent/harness.py`: `ThreadPoolExecutor` precedent.
- `omega_prime/tools/registry.py`: register(name, description, parameters,
  handler, requires_approval); dispatch returns JSON strings; unknown name
  ⇒ JSON error, never raises.
- Roster: `contracts/tool-rosters/omega-prime.yaml` — append family names
  in registration order + header comment line (drift-guard tested).
- `session/persist.py`: session persistence for create_session durability.

</code_context>

<specifics>
## Specifics

**New tools (family `rlm`, `RLM_TOOL_NAMES`):** `rlm_spawn`, `rlm_collect`,
`rlm_list_subagents`, `rlm_delete_subagent`, `rlm_create_session`,
`rlm_progress_note`, `rlm_rename`. All read-only except spawn /
create_session / delete / rename (writes ⇒ `requires_approval` per the
desk write-gate precedent — spawn admits a child run, which is a write).

**Tests (`omega_prime/tests/test_rlm.py`):** scripted-model children;
spawn→collect happy path; timeout snapshot semantics; selector
normalization (handle/row/name/list); unknown-target error strings;
throttle accept/reject with retry_after_ms; delete reaps result;
depth-cap behavior; disabled-family degraded errors; roster drift guard
extended; registration behind the `prime.rlm.enabled` config flag
(default off — flag plumbing lands with the config surface; if Phase 57's
config module is not yet in place, this phase introduces the minimal
`omega_prime/config.py` it needs, JSON + `OMEGA_PRIME_*` env overrides).

**Acceptance:** v10-REQUIREMENTS RLM-01..04; full suite + evals +
assemble check green.

</specifics>
