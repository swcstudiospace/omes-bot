# Phase 61: Prime loop gap closure — Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 11 planned new/modified files and 2 read-only source analogs
**Analogs found:** 13 / 13 (11 exact role/data-flow matches; 2 role matches)

## Scope and precedence

Use `61-CONTEXT.md` as the interface authority and the final checked plans as the writable ownership lists. No RESEARCH.md is required for this bounded gap closure. This map does not add options, architecture, dependencies, or implementation scope.

The five pattern families below are sufficient: existing turn orchestration, guarded hooks/typed views, capability registration, JobStore/APScheduler delivery, and consumer behavior tests. All paths named as analogs were confirmed by `git ls-files -- <paths>`. Current runtime glue was also inspected as a target, not substituted for a tracked analog.

## File Classification

| Target or Read-only Analog | Change | Role | Data Flow | Closest Tracked Analog | Match Quality |
|---|---|---|---|---|---|
| `omega_prime/tools/registry.py` | modify | utility | request-response | same file | exact |
| `omega_prime/tools/goals.py` | modify | controller | CRUD / request-response | same file | exact |
| `omega_prime/tools/autonomous.py` | modify | controller | request-response / event-driven | same file | exact |
| `omega_prime/agent/conversation_loop.py` | modify | service | request-response | same file | exact |
| `omega_prime/agent/runtime.py` | modify | service | request-response / event-driven | `omega_prime/agent/conversation_loop.py` | role-match |
| `omega_prime/agent/prime_hooks.py` | new | utility | event-driven / transform | `omega_prime/agent/degraded.py` | role-match |
| `omega_prime/tests/test_prime_loop.py` | new | test | request-response | `omega_prime/tests/test_loop.py` | exact |
| `omega_prime/agent/session_lease.py` | modify | utility | event-driven | `omega_prime/agent/harness.py` (`PauseGate`) | exact |
| `omega_prime/cron/scheduler.py` | read-only | model | file-I/O / batch | same file (`JobStore`) | exact |
| `omega_prime/cron/heartbeat_runtime.py` | new | service | event-driven / file-I/O | `omega_prime/cron/apscheduler_backend.py` | exact |
| `omega_prime/cron/apscheduler_backend.py` | read-only | service | event-driven | same file | exact |
| `omega_prime/tools/heartbeat.py` | modify | controller | CRUD / request-response | same file | exact |
| `omega_prime/tests/test_heartbeat_runtime.py` | new | test | event-driven / file-I/O | `omega_prime/tests/test_apscheduler_backend.py` | exact |

“Exact” means matching role and data flow, not that the new capability already exists. Plan 01 owns the first seven targets; Plan 02 owns the remaining four targets. The two cron neighbors are read-only analogs, not writable targets.

## Pattern Assignments

### `omega_prime/tools/registry.py` — generic runtime attachment

**Analog:** same file, imports 11–17 and constructor 31–43. Copy its per-instance typed dictionary convention (lines 38–43):

```python
self._tools: dict[str, _Tool] = {}
self._order: list[str] = []
self._approval_log = approval_log
self._policy = policy
self._audit = audit
self._tracer = tracer
```

Add only the locked empty `runtime_bindings: dict[str, Any]` instance dictionary. It is resource attachment, not a second tool map. Keep `dispatch` as the policy/approval/audit/serialization boundary (83–117; excerpt in Shared Patterns). No process/global cache or closure introspection.

### `omega_prime/tools/goals.py` — publish the existing fresh-store factory

**Analog:** same file, imports 12–17, enable guard 38–39, factory 41–42:

```python
def store() -> PrimeGoalStore:
    return PrimeGoalStore(Path(root) / "goals")
```

Publish this same callable as `prime_goals`, not a store instantiated at registration. Preserve handler ordering, drift check, schemas, and approval flags (67–85). The hook must call the factory again at boundaries so dispatched and external writes are authoritative. Follow `test_goals_prime.py:125–166` for real registry dispatch, disabled registration, and write-tool approvals. Disabled registration must not leave a usable runtime binding.

### `omega_prime/tools/autonomous.py` — publish the same live holder

**Analog:** same file, imports 14–19 and holder at 47:

```python
state: dict[str, AutonomousDriver | None] = {"driver": None}
```

Start creates/starts a driver and replaces the holder entry (49–77). Stop deliberately clears that same entry (86–88):

```python
driver = state["driver"]
state["driver"] = None
return {"stopped": True, "was_running": bool(driver and driver.running)}
```

Publish `state` as `prime_autonomous`; hooks dereference it live, not a driver snapshot. Preserve registration and approval handling (90–108). Copy tool-dispatch tests from `test_autonomous.py:98–129`; do not introduce a second driver or restart a stopped driver at a boundary.

### `omega_prime/agent/conversation_loop.py` — continuation inside the existing bounds

**Analog:** same file, absolute imports 19–41, optional Agent fields 79–103, turn envelope 122–151, and action loop 194–260. Current billing/cap ordering (211–217):

```python
if not budget.consume():
    turn_exit_reason = "budget_exhausted"
    break
api_call_count += 1
started = time.monotonic()
assistant_message = agent.model.complete(messages, original_tools)
_trace_model_call(agent, started)
```

Keep the cumulative `api_call_count < agent.max_iterations` condition (194) and the same budget object across implicit continuations. The current function resets its local count at 175 and refills only its agent-created budget at 181–187: those entry semantics cannot be applied afresh to each implicit continuation. Explicit later user turns retain the normal default-budget refill. Add no continuation-round cap.

Reuse prompt/history handling (162–173, 328–346), pause/interrupt/before-model ordering (195–210), steer and tool marks (222–247), journal helpers (373–405), finalization (277–292), and `restore_tools` in `finally` (293–294). `turn_finalizer.py:41–51,63–78` is the existing completed/interrupted/failed result contract; a nonempty response alone is not a completed turn. Provider calls remain outside hook degradation wrappers.

### `omega_prime/agent/runtime.py` — compose and re-enter the owning agent

**Tracked analog:** `conversation_loop.py:79–151` for optional loop resources and its lease-owned run envelope; `tools/registry.py:83–117` for the execution authority. Borrow the envelope, not a fresh-agent cron runner. Its terminal cleanup is unconditional (150–151):

```python
finally:
    lease.release()
```

Preserve the target's existing offered-schema filtering, registry dispatchers, provider wrapper, `self.messages`, and `self.system_message`. Bind the live runner before starting the registry-owned heartbeat runtime. The runner re-enters this instance with the same transcript and opt-in lease waiting; `run_due_jobs` in `scheduler.py:118–132` intentionally creates a new Agent and is **not** the heartbeat-session pattern.

Use only the Context seam: `bind(name, runner, *, event_sink=None)` and `unbind(name, *, runner=None)`. Retain the runner identity used for binding; close performs the expected-runner comparison atomically inside unbind. A replaced agent must neither detach its replacement nor stop scheduling for another live binding. Named sinks belong to named runners, not a mutable shared agent-sink attribute. Flags off means no heartbeat lifecycle/thread creation.

### `omega_prime/agent/prime_hooks.py` — guard the capability boundary, consume typed views

**Analogs:** `degraded.py:12–17,20–44` for imports/error isolation; `prime/goals.py:85–109` and `prime/autonomous.py:107–133,176–177` for typed views. The concrete wrapper and connector excerpts appear in Shared Patterns.

Read the registered goal factory and driver holder live. Keep once-per-logical-turn accrual separate from continuation decisions, including usage already known when a later provider call fails. The goal port already owns stale/budget/continuation semantics (`agent/goals.py:125–166`); the driver already owns limits, sticky stops and real argv gates (`agent/autonomous.py:104–177`). Do not duplicate either state machine. Hook degradation cannot create or extend continuation, and cannot hide provider exceptions, interrupts, or policy refusals.

### `omega_prime/tests/test_prime_loop.py` — actual loop/registry consumer regressions

**Primary analog:** `test_loop.py`, imports 9–14, tool-call helper 17–28, prompt/history checks 110–200, stop/budget checks 203–309, and failure/lease checks 312–345. Copy concrete consumer assertions, e.g. 131–134:

```python
assert second["content"] == first["content"]
assert second["content"].encode("utf-8") == first["content"].encode("utf-8")
assert second["content"] is first["content"]
assert result["messages"][0]["content"] is first["content"]
```

Combine with real registry approvals/dispatch from `test_goals_prime.py:131–145` and `test_autonomous.py:107–120`, then drive actual `OmegaPrimeAgent` turns. `agent/model.py:17–44` supplies `ScriptedModel.seen`, `tools_seen`, `call_count`, and `remaining`; exhausted scripts return empty text, so assert call counts and remaining responses rather than allowing exhaustion to conceal runaway continuation.

Consumer cases must include cumulative caps and a spent caller budget; goal/driver changes through tools and external store handles; all-round known usage plus successful usage preceding a later provider failure; original exception propagation and released lease; real gate stop reasons; redacted hook degradation/no continuation; and flags-off transcript/roster/prompt/lifecycle preservation. `test_autonomous.py:60–84` uses real `/bin/true` and `/bin/false` argv gates. Config defaults are exercised in `test_prime_config.py:15–18`; those defaults alone do not prove production flags-off behavior.

### `omega_prime/agent/session_lease.py` — atomic wait and ownership

**Analogs:** retain the existing lease's default acquisition/error (26–30); copy synchronization from `harness.py`'s `PauseGate`, constructor 237–241, resume 265–277, wait 290–297. Its predicate/wait pattern (292–297):

```python
with self._cond:
    while self._paused:
        if interrupt is not None and interrupt.is_set():
            return False
        self._cond.wait(timeout=poll_s)
    return True
```

Copy the Condition discipline, **not** the pause-specific interrupt/polling policy or `default_pause_gate`. For locked `acquire(*, wait=False)`, Condition must use the lease's existing lock; predicate checking, waiting, and taking `_held` are atomic. `release` clears `_held` and notifies waiters under the same Condition. Keep the fast-fail `RuntimeError("session lease already held")`, `held`, and context-manager behavior; BaseException propagation stays intact. Test the public primitive and real-loop lease behavior, not lock implementation text.

### `omega_prime/cron/scheduler.py` — persisted claim/history schema

**Analog:** same file, imports 10–17, `HISTORY_LIMIT = 20` (19), job schema 39–49, load/save 97–115. Claim/finish sequence (81–87):

```python
job["claimed_at"] = now
self._save()
job["last_result"] = runner(job["prompt"])
job["last_ran_at"] = now
history.append({"ran_at": now, "result": job["last_result"]})
del history[:-HISTORY_LIMIT]
job["claimed_at"] = None
```

Reuse these fields and bounded history, plus completion/interval semantics (88–93). This is a persistence pattern, **not** permission to run callbacks while holding runtime bookkeeping locks. Heartbeat runtime needs claim, unlocked callback, then fresh-store conditional finish. Do not save an old whole-store snapshot after a callback: clear/schedule may have changed disk state. Preserve `JobStore.tick` and existing generic cron behavior; no second file/schema.

### `omega_prime/cron/heartbeat_runtime.py` — live APS delivery with split bookkeeping

**Analogs:** `apscheduler_backend.py:12–19,25–77` for APS lifecycle, `scheduler.py:22–115` for persistence, and `cron/heartbeat.py:25–64,82–111` for the heartbeat kind and named routing. Schedule's existing persisted annotations (45–46):

```python
job["kind"] = HEARTBEAT_KIND
job["session"] = session
```

Reuse positive-interval/nonempty-session validation (`cron/heartbeat.py:38–41`) and explicit unknown-job results (57–64). Capture a named runner and its optional sink together under the runtime lock; perform lease waiting and callbacks outside it. Unknown names are errors, never a default/fresh conversation. Conditional unbind compares the expected runner under that same lock.

Start/restart reloads current persisted heartbeats and reconciles scheduler entries; foreign cron kinds remain untouched. Claim and finish reload disk; finish must not resurrect a cleared job or overwrite a concurrent update. Use `HISTORY_LIMIT`, not `tick_heartbeats`' literal slice bound. A non-JSON result is a structured error plus redacted degradation, never `repr`/`default=str` success. The constructor's optional service sink is only for undirected diagnostics; directed failures use the captured named sink. Guard sink failure without losing the already-recorded beat error. Stop/rebind must not release another named session's ownership.

### `omega_prime/cron/apscheduler_backend.py` — reuse entry construction, preserve generic service

**Analog:** same file; dependency imports 12–19, UTC conversion 90–91, interval entry construction 53–61:

```python
self.scheduler.add_job(
    self._fire,
    "interval",
    seconds=interval,
    start_date=_at(job["due_at"]),
    id=job["id"],
    max_instances=1,
    coalesce=True,
)
```

One-shots use `"date"`, `run_date=_at(...)`, and the same persisted id (63–65). Follow these conventions locally in HeartbeatRuntime; do not extract a shared helper or modify SchedulerService. Its overdue startup tick (42–43), safe pre-start stop (71–77), and `_fire` lock across `store.tick` (83–87) remain unchanged. **Do not copy that lock/callback scope into lease-waiting heartbeats**. A runtime in-flight guard is still needed; scheduler `max_instances=1` alone does not protect direct/startup fire paths or fresh-store merges.

### `omega_prime/tools/heartbeat.py` — delegate persistence and live scheduler sync

**Analog:** same file, imports 12–23, family names/write flags 26–32, disabled guard 42–43, store path 45–46, handler returns 48–67, registration 69–85. Existing response/default semantics (59–61):

```python
    due_at=time.time() if due_at is None else due_at,
)
return {"scheduled": job_id, "session": session}
```

Keep schemas/names/approvals and those external result shapes. Enabled tools delegate schedule/list/clear to the runtime published at `prime_heartbeat`, synchronizing live entries as well as persisted state. Same resolved path on the **same registry** reuses its existing bound runtime; do not introduce multi-registry authority or a global runtime cache. Disabled registration constructs/publishes no runtime. Copy dispatch-based round trips and disabled behavior from `test_heartbeat.py:78–115`; do not test only private handlers.

### `omega_prime/tests/test_heartbeat_runtime.py` — observable delivery, history, overlap, shutdown

**Analogs:** `test_apscheduler_backend.py`, imports 5–10, bounded observation helper 13–19, real delivery/persistence 34–49, restart 86–105, lifecycle 121–131; `test_heartbeat.py:43–75` for named routing and foreign-kind/clear behavior. The real scheduler test closes even on assertion failure (46–49):

```python
    persisted = json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8"))
    assert persisted["jobs"][0]["last_result"] == "done"
finally:
    service.stop()
```

Adapt to the live named runner and reopen `JobStore` for history/due/claim assertions. Use controlled thread events and bounded joins for foreground overlap, clear/reschedule during callbacks, and sink/runner replacement; mere sleeps or scheduler wiring assertions do not prove atomic behavior. Include lease wait/default-fast-fail, unknown names/ids, same-path reuse, restart resync, foreign-kind isolation, non-JSON failures, redaction, captured named sinks, expected-runner unbind, failure followed by another beat, and final shutdown. Keep a real APScheduler delivery smoke, not solely an injected scheduler double.

## Shared Patterns

### Authorization and JSON errors stay in registry dispatch

**Source:** `omega_prime/tools/registry.py:90–100`. **Apply to:** all three tool families and runtime dispatchers; hooks never grant/invoke tool handlers outside dispatch.

```python
if self._policy is not None and not self._policy.allows_tool(name):
    self._record(name, "denied", reason="policy forbids")
    return _dump({"error": f"policy forbids {name}", "tool": name})
try:
    if tool.requires_approval and not _has_approval(self._approval_log, name):
        self._record(name, "denied", reason="approval required")
        return _dump({"error": "approval required", "tool": name})
    payload = _call(tool.handler, _arguments(arguments))
except Exception as exc:
    self._record(name, "error", reason=f"{type(exc).__name__}: {exc}")
    return _dump({"error": f"{type(exc).__name__}: {exc}"})
```

Dispatch rejects unserializable results (111–115). Do not convert ordinary refusal into successful degradation or continuation.

### Guard only Prime hooks; emit through redaction

**Source:** `omega_prime/agent/degraded.py:34–44`. **Apply to:** Prime boundary hooks, not foreground model execution.

```python
try:
    return hook(*args, **kwargs)
except Exception as exc:  # degrade-with-warning contract
    emit(
        agent,
        "prime_degraded",
        family=family,
        error=f"{type(exc).__name__}: {exc}",
        turn_id=turn_id or uuid.uuid4().hex,
    )
    return None
```

`harness.py:50–52` supplies the common event path:

```python
event = {"type": type, **_redact_payload(payload)}
events_of(agent).append(event)
return event
```

`_redact_payload` only redacts top-level **string** payload values (55–61); nested exception/result objects are not automatically sanitized. Pass a flat error string through emit, not raw exception/repr objects or direct event-list appends. Hook failure's None must fail closed for continuation. Catch Exception, never BaseException. Copy the secret-bearing exception assertion from `test_prime_degraded.py:50–58` into production-consumer regressions. Background runner Exceptions have their separate structured beat-error path; that does not change foreground provider propagation.

### Typed views validate boundaries without new stores/drivers

**Sources:** `omega_prime/prime/goals.py:151–152` and `omega_prime/prime/autonomous.py:176–177`:

```python
def status(self) -> dict:
    return GoalStatusView.from_status(self._store().prime_status()).to_dict()
```

```python
def after_turn(self, driver: AutonomousDriver, result: dict) -> dict:
    return VerdictView.from_verdict(driver.after_turn(result)).to_dict()
```

Copy view consumption, **not** a second connector-owned resource: use the bound factory/holder. `GoalStatusView.from_status` enforces active/paused/completed/cleared; `VerdictView.from_verdict` enforces continue/stop and the existing closed stop reasons. Existing typed views are dataclasses; **model usage is not**. Malformed hook payload handling belongs inside guarded capability boundaries.

### Usage: per-successful-call dictionaries, then one logical-turn accrual

**Sources:** `omega_prime/providers/base.py:142,200–213,215–232`, `conversation_loop.py:356–364`, and `agent/goals.py:43–53`. `ProviderModel.last_usage` is `dict[str, int] | None`; both normal and streaming success assign it before returning. Loop tracing already reads via `getattr` and excludes bool counters. Goal arithmetic is concrete and reusable:

```python
if not isinstance(usage, dict):
    return 0
total = usage.get("total_tokens")
if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
    return total
delta = 0
for key in ("prompt_tokens", "completion_tokens"):
    value = usage.get(key)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        delta += value
return delta
```

Capture known usage after **each successful** model call, before another call can replace metadata. Accrue once per logical turn, including tool rounds and known successful calls before a later raise. Do not count stale last_usage again when a failing call returns no response, invent unknown tokens, double-count total plus component counters, or add speculative usage-dataclass branches. The driver consumes `result['usage']['total_tokens']` (`agent/autonomous.py:198–205`). Keep native assistant/provider metadata lossless; tracer normalization is not a license to strip response rows. Accrual cleanup must not replace the original provider exception.

### External completion and hermetic consumers

`PrimeGoalStore.complete()` (`agent/goals.py:106–112`) marks completed and returns the report; `test_goals_prime.py:96–107` demonstrates the actual handle-driven completion path. The registered family has no goal-complete tool (`tools/goals.py:20–26`). Use a separate store handle to complete during a regression and prove fresh boundary reads/report propagation. Completing all steps only removes the continuation prompt; do not invent automatic completion semantics.

Use `tmp_path` persisted stores and the existing sandbox conventions. `tests/conftest.py:15–22` redirects PyRIT's XDG data location before imports; preserve it. No new network/model SDK is needed for these consumer tests.

## No Analog Found

No whole target lacks a role/data-flow analog. These **new behavioral subpatterns** have no complete existing implementation to copy and must follow the reviewed Context rather than fabricated source precedent:

| Target | Subpattern without a complete existing analog |
|---|---|
| `agent/prime_hooks.py`, `agent/conversation_loop.py` | Bounded production continuation plus once-per-turn usage accrual across a later provider failure. Existing library/hook/loop pieces must be integrated, not treated as existing end-to-end proof. |
| `agent/runtime.py`, `cron/heartbeat_runtime.py` | Atomic expected-runner unbind, captured runner/sink ownership, and named live-session re-entry. Generic cron's fresh Agent and shared sink mutation are not substitutes. |
| `cron/heartbeat_runtime.py` | Fresh-store conditional finish after an unlocked callback, live schedule reconciliation, and structured non-JSON failure. Existing synchronous tick alone does not establish concurrent lost-update safety. |

## Metadata

**Analog search scope:** only assigned targets and their directly relevant `omega_prime/agent`, `omega_prime/tools`, `omega_prime/prime`, `omega_prime/cron`, provider usage, and named neighboring test sources; no upstream or unknown subsystem search.
**Files scanned:** 29 source files (28 ranged reads; one additional current provider source inspected by targeted usage search).
**Tracked-source gate:** every named analog returned by `git ls-files`; no install/runtime mirror used as a pattern origin.
**Pattern extraction date:** 2026-10-08.
**Execution evidence:** source inspection and tracked-membership lookup only. No product edits, builds, tests, lint, types, formatters, commits, or publication. Parent owns post-integration verification; this map records patterns and pitfalls, not exercised acceptance results.
