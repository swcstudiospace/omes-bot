# AI-SPEC — Phase 61: Prime loop gap closure

> Advisory `plan:pre` AI-integration contract, version **1.0.0**, for the existing v10 gap closure. Consumed by the phase planner and evaluation reviewer; it is not implementation evidence or an external API contract.
> The reviewed [61-CONTEXT.md](61-CONTEXT.md) governs all decisions. This document does not reopen framework/provider selection or authorize work outside the two disjoint implementation units.

## Contract provenance and four-stage resolution

This trusted-host standalone `design.contract` assignment has one writer. The four stages were resolved sequentially within this artifact: **selection** (§2), **implementation guidance** (§3–4b), **domain/failure context** (§1–1b), and **evaluation** (§5–7). The host does not expose `gsd-framework-selector`, `gsd-ai-researcher`, `gsd-domain-researcher`, or `gsd-eval-planner`; none is claimed to have run. The GSD workflow, framework/eval references, and `AI-SPEC.md` template were read, not used to introduce their default SDKs or tracing dependencies.

Evidence labels throughout:

- **[CONTRACT]** — required behavior from `61-CONTEXT.md`, `.planning/REQUIREMENTS.md`, or this assignment; not a claim that the behavior exists yet.
- **[SOURCE]** — observed repository code or existing test definitions. Reading a test is not running it.
- **[OFFICIAL]** — official library documentation, used only for the existing threading/scheduler primitives and the template's validation example.
- **[INFERENCE]** — design/evaluation reasoning derived from the sources; not an observed runtime result.
- **[PARENT-REPORTED]** — supplied pre-change evidence, accepted without rerunning it.

**Scope:** close LOOP-01/02/03/06; preserve LOOP-04/05/07. DONE-01/02 remain parent-owned and require exercised evidence. No product source, upstream tree, dependency, planning-state, infrastructure, or release change is made by this advisory hook. No builds, tests, lint, typechecks, formatters, smoke runs, commits, or publication were performed here. Swarm lifecycle/ADR/OpenAPI publication is not part of this standalone internal-boundary contract.

---

## 1. System Classification

**System Type:** Autonomous Agent with conversational/tool-use turns and optional scheduled re-entry; not a new multi-agent framework, RAG system, or native session engine.

**Description:** Developers operate one Python `OmegaPrimeAgent`, composed over `Agent` / `run_conversation`, with registry-governed tools and a persistent session transcript. The existing native `PrimeProviderModel` supplies completions; Prime goals/autonomy/heartbeats are optional capabilities of this same loop. Good behavior means registered state actually affects the production turn, every continuation remains bounded and policy-governed, stops tell the truth, and scheduled prompts re-enter the exact named live session without losing its history. [SOURCE: `omega_prime/agent/runtime.py::OmegaPrimeAgent`, `conversation_loop.py::run_conversation`, `providers/prime.py::PrimeProviderModel`; CONTRACT: Context, locked decisions]

**Critical Failure Modes:**

1. Successful model calls are undercounted, counted twice, or erased by a later provider failure, defeating goal/autonomy token budgets.
2. Implicit continuation resets the model-call/iteration budget, ignores interrupt or stop state, or restarts a stopped driver.
3. Limit exhaustion, a gate result, a provider error, or failed result serialization is represented as successful task completion.
4. A hook failure suppresses the original provider/control-flow exception, leaks secrets, or itself enables more continuation.
5. A heartbeat reaches a new/wrong session, interleaves transcript writes, deadlocks with a foreground tool, loses persisted updates/history, or lets an old agent's close detach its replacement.

These are evaluation targets, not new observed incidents. The two supplied boundary reproductions below are the known pre-change evidence. [CONTRACT; INFERENCE]

### Requirements allocation

| Requirement | Boundary covered by this contract | Evidence required from parent |
|---|---|---|
| LOOP-01 | Fresh goal reads, authoritative lifecycle, exact usage accrual, bounded continuation | Real agent + real goal store regression and native HTTP smoke |
| LOOP-02 | Named live binding, lease wait, APScheduler lifecycle, durable job history | Deterministic ownership/overlap tests plus real scheduler smoke |
| LOOP-03 | Existing driver, turn/token/time limits, actual gate, honest sticky stops | Real driver/argv regressions through the production loop |
| LOOP-06 | Guarded capability failures and explicit heartbeat errors | Failure injection through the real boundary with redacted events |
| LOOP-04/05/07 | Existing messaging, flags-off tools/prompts/transcripts and fast-fail behavior | Unmodified neighbors and flags-off parity gate |
| DONE-01/02 | No new completion claim from this design artifact | Parent records commands, exit codes, smoke evidence, then reconciles milestone records |

No public-API latency SLO, cost target, provider expansion, or new round-limit requirement is introduced. Existing configured budgets and correctness constraints are the measurable limits. [CONTRACT]

---

## 1b. Domain Context

**Industry Vertical:** Developer tooling and bounded programming-agent automation. [SOURCE: `pyproject.toml`, `docs/agent-loop.md`]

**User Population:** Developers operating local tool-enabled sessions; maintainers reviewing deterministic behavior and runtime evidence. [SOURCE: `CONTRIBUTING.md`; INFERENCE: operator roles]

**Stakes Level:** High for control-boundary correctness: the loop can invoke approved write tools and configured terminal quality gates. This is an evaluation risk classification, not a newly accepted security risk. [SOURCE: `tools/registry.py::dispatch`, `agent/autonomous.py::_run_gate`; INFERENCE]

**Output Consequence:** Model/tool rows become future model context and journal material; heartbeat results become persisted job history. A false success or wrong-session callback can mislead a developer and corrupt subsequent work, while a fabricated token count can undermine an operator's configured spending bound. [SOURCE: `agent/turn_tool_round.py`, `agent/turn_finalizer.py`, `cron/scheduler.py`; INFERENCE]

### What Domain Experts Evaluate Against

| Dimension | Good — maintainer accepts | Bad — maintainer flags | Stakes | Source |
|---|---|---|---|---|
| Real usage | Every known successful-call counter contributes once, including tool rounds; earlier usage survives a later failure | Final-call-only usage, double charging cache counters, invented tokens for unknown usage | High | `providers/prime.py::_usage`, `agent/goals.py::goal_token_delta_for_usage`; Context |
| Control precedence | Interrupt/incomplete/failure/refusal and authoritative goal/driver stop state prevent implicit re-entry | Goal prompt overrides a stop; continuation gets a fresh budget | High | `conversation_loop.py`, `turn_finalizer.py`, `agent/autonomous.py`; Context |
| Honest outcome | Goal completion comes from stored completion state; gate/limit outcome says exactly what it verifies | Any text answer, passed gate, or exhausted limit claims the objective was completed | High | `PrimeGoalStore.complete/completion_report`, autonomous stop constants and notes |
| Session identity | A beat's prompt is appended to its named live agent after exclusive acquisition; metadata/history survive | Fresh agent per beat, cross-session error sink, stale close removes replacement | High | `runtime.py`, `session_lease.py`; Context's planned named-binding contract |
| Failure containment | Recoverable Prime hook failures emit redacted structured events and do not extend continuation | Provider error becomes degradation-only success; non-JSON result becomes a raw `repr` marker | High | `degraded.py::guarded_hook`, `harness.py::emit`, `registry.py::dispatch`; Context |
| Compatibility | All-off behavior and existing messaging remain unchanged, with no scheduler startup | New Prime rows/tools/events or background threads appear when disabled | High | `config.py`, `test_prime_regression.py`, `test_agent_message.py`; Context |

### Known Failure Modes in This Domain

- **[PARENT-REPORTED]** Active autonomy with `max_turns=2` produced one model call, with driver `turns=0` and `running=True`. This demonstrates registered state being ignored, not a provider benchmark.
- **[PARENT-REPORTED]** An active goal with token budget 10 and model usage 7 produced one model call and persisted `tokens_used=0`.
- **[SOURCE]** The current loop stops at its first text verdict and has no Prime turn hook. The current finalizer contains no usage field; `_RegisteredModel.last_usage` only forwards the provider's latest call. Helper tests alone therefore cannot establish production integration.
- **[SOURCE]** `PrimeGoalStore` loads on construction; caching one instance across externally updated boundaries would read stale lifecycle state. Autonomous tool handlers close over a per-registry holder, so duplicating a driver would make start/status/stop diverge.
- **[SOURCE]** Current heartbeat helpers accept a session callback but do not own live-agent binding or scheduler lifecycle. `SchedulerService._fire` holds its bookkeeping lock during `store.tick(..., runner)`. Copying that lock scope into a waiting heartbeat path would risk foreground/background deadlock. [INFERENCE]
- **[INFERENCE]** APScheduler's per-job `max_instances` does not serialize all access to a session transcript; the session lease and mutation-safe bookkeeping are still necessary.

### Regulatory / Compliance Context

No healthcare, financial, or other sector-specific regulation is established by the phase inputs. Do not infer compliance certification. Existing applicable repository constraints are AGPL-3.0-only licensing/MIT source attribution, read-only upstream references, broker-owned credential handling, secret redaction, and existing policy/approval checks. This phase adds no provider or data processor. A formal privacy/legal classification is not supplied and is not needed to choose this internal boundary fix. [SOURCE: `pyproject.toml`, `CONTRIBUTING.md`, source SPDX/attribution headers; CONTRACT]

### Domain Expert Roles for Evaluation

| Role | Responsibility |
|---|---|
| Loop implementer/maintainer | Define exact usage, continuation, completion, and stop expectations from the real store/driver/loop |
| Scheduler implementer/maintainer | Label identity, concurrency, lost-update, restart, history, and shutdown scenarios |
| Parent integration owner | Exercise native HTTP and real scheduler paths, inspect evidence, adjudicate parity, and own all final verification/state changes |
| Evaluation/review consumer | Check each rubric against commands and artifacts; reject wiring-only, skipped-native, or invented-success evidence |

These roles define review responsibility; no specialist research or gate verdict is claimed. [CONTRACT]

---

## 2. Framework Decision

**Selected Framework:** The repository's current Python `Agent` / `run_conversation` and `OmegaPrimeAgent` composition, using the existing native `PrimeProviderModel` / `ai.complete` bridge and existing APScheduler background scheduling.

**Version:** `omega-prime` 0.1.0, Python >=3.11 (`pyproject.toml`); native extension `omega_prime_prime` 0.1.0 (`native/omega-prime-prime/Cargo.toml`); Prime source pin `967eb13fd488507af5f590e9c6ea8b2672f1fc05` (`omega_prime/contracts/prime-agent.pin.json`). The committed Python lock records APScheduler 3.11.3. These are file-declared versions, not measurements of the installed environment. No dependency change is authorized. [SOURCE]

**Rationale:** The reviewed Context already selects the one existing loop, native provider/catalog bridge, goal store, driver, guarded-hook utility, JSON job store, and scheduling convention. The gap is missing consumption of existing registered resources at production boundaries, not missing model capability or a need for another orchestration framework. [CONTRACT; SOURCE]

**Alternatives Considered:** No new framework selection exercise was performed. The template's alternatives field records scope exclusions, not implementation candidates or researched comparisons.

| Excluded change | Ruled out because |
|---|---|
| New agent SDK, provider, or API surface | Context locks the existing stack; this phase changes internal control boundaries only |
| Native `SessionEngine`, TUI/daemon ownership, or agent subprocess replacement | Explicitly excluded by the existing-v10 gap-closure boundary |
| Process/global runtime cache or multi-registry service architecture | Named sessions share one authoritative registry-bound heartbeat runtime; same-path re-registration reuses it |

**Vendor Lock-In Accepted:** Existing explicit native-provider selection is retained, not broadened. `PrimeProviderModel` requires a full camelCase model descriptor and an explicit key/options key or broker resolution; there is no ambient-key or Python-provider fallback. This document does not claim live-service authentication for every native provider. [SOURCE: `providers/prime.py::__init__/complete`; `docs/agent-loop.md`]

---

## 3. Framework Quick Reference

> Resolved inline from current repository sources and the limited official references cited below. Planned seams are marked [CONTRACT], not presented as already implemented methods.

### Installation

Reuse the parent's existing `.venv` and already available native extension. No installation or build is required by this advisory assignment. The repository install/lock instructions are in `CONTRIBUTING.md` and `requirements-lock.txt`; do not upgrade or add a dependency to implement this phase. The parent must report an unavailable native extension as a smoke prerequisite, not accept the native suite's skip as proof. [CONTRACT; SOURCE: `prime_kernel/native.py::load_extension`, `test_prime_runtime_e2e.py::native_ai`]

### Core Imports

Existing production imports, not a new framework layer:

```python
from omega_prime.agent import OmegaPrimeAgent
from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.goals import PrimeGoalStore
from omega_prime.agent.autonomous import AutonomousDriver
from omega_prime.agent.degraded import guarded_hook
from omega_prime.tools.registry import ToolRegistry
from omega_prime.providers.prime import PrimeProviderModel
```

### Entry Point Pattern

This factory uses the current, source-defined entry point. The caller retains the returned agent and calls `agent.run(...)` on that same instance across foreground turns; it must not recreate an agent for each heartbeat. No new provider descriptor or credential is invented here.

```python
def make_session(
    descriptor: dict, api_key: str, registry: ToolRegistry
) -> OmegaPrimeAgent:
    return OmegaPrimeAgent.from_prime(
        descriptor,
        registry=registry,
        api_key=api_key,
        provider_options={"timeoutMs": 60_000},
        system_message="Use only the offered registry tools. Respect approvals.",
    )
```

[SOURCE: `agent/runtime.py::from_prime/run`, `docs/agent-loop.md` entry-point example]

**Planned composition change:** add optional stable `session_name` (default `default`), close/context-manager lifecycle, and opt-in `wait` forwarding; bind the live runner before starting an enabled runtime. These additions are contract requirements, not currently source-defined constructor/run parameters in the inspected baseline. [CONTRACT]

### Key Abstractions

| Concept | What it is | When used |
|---|---|---|
| `ToolRegistry` | Offered schemas, executable handlers, policy/approval/audit authority | Every model tool request still dispatches through it |
| `runtime_bindings` | Planned generic `dict[str, Any]`, empty by default | Attach the same resources already owned by enabled registrations, without granting tools |
| `prime_goals` | Existing zero-argument store factory, published as a binding | Reload goal state at each relevant boundary |
| `prime_autonomous` | Existing mutable `{"driver": AutonomousDriver \| None}` holder | Read the current started/stopped driver, not a cached copy |
| `prime_heartbeat` | Planned `HeartbeatRuntime` for the persisted jobs path | Synchronize heartbeat tools and named live session re-entry |
| `SessionLease` | Exclusive ownership of a session turn | Foreground fast-fails by default; heartbeat uses planned atomic `wait=True` acquisition |
| `last_usage` | Provider's latest successful-call dict, or `None` | Capture each call before the next call resets it; aggregate without changing native rows |
| `GoalStatusView` / `VerdictView` | Existing typed connector views | Reuse where their existing contracts expose the boundary; do not replace them with new schemas |

[SOURCE: registry, goal/autonomy tools, lease, provider, and `omega_prime/prime/{goals,autonomous}.py`; CONTRACT: attachment/runtime additions]

### Common Pitfalls

1. Recursively calling the public turn function for implicit continuation would reacquire/reset turn machinery; stay inside the existing lease/run/transcript/cumulative budget. [CONTRACT]
2. Reading only final `last_usage`, summing `total_tokens` together with its component/cache counters, or calling `after_turn` once per tool-model call corrupts accounting. Capture per call; charge unconsumed logical-turn usage once. [SOURCE; CONTRACT]
3. Treating `guarded_hook` as a provider-error wrapper or timeout watchdog is incorrect. It catches `Exception` from the supplied hook; it does not impose a deadline and does not catch `KeyboardInterrupt`/`SystemExit`. [SOURCE: `degraded.py`]
4. APScheduler `shutdown(wait=False)` does not terminate already executing callbacks. Do not claim immediate quiescence from that option; successful wait/close evidence must show settlement without holding a lock needed by the callback. [OFFICIAL: [APScheduler 3.x user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html#shutting-down-the-scheduler)]
5. A condition notification does not transfer ownership: waiters reacquire the lock and recheck the predicate before setting the held flag. A check-then-acquire loop is not an atomic lease. [OFFICIAL: [Python 3.11 condition objects](https://docs.python.org/3.11/library/threading.html#condition-objects)]
6. Scheduler entries are an in-memory projection, not a second durable authority. Reconcile IDs/triggers from current persisted heartbeats; do not tick foreign cron kinds through a heartbeat runner. [SOURCE: `cron/apscheduler_backend.py`, `cron/heartbeat.py`; CONTRACT]

### Recommended Project Structure

Keep the existing ownership/layout; no new service or framework folder:

- **61-01 loop unit:** `agent/conversation_loop.py`, `agent/runtime.py`, planned `agent/prime_hooks.py`, generic `tools/registry.py` attachment, goal/autonomy registrations, planned `tests/test_prime_loop.py`.
- **61-02 heartbeat unit:** `agent/session_lease.py`, existing cron helpers/backend/store, planned `cron/heartbeat_runtime.py`, `tools/heartbeat.py`, planned `tests/test_heartbeat_runtime.py`.
- **Read-only contracts/provider baseline:** `prime/goals.py`, `prime/autonomous.py`, `providers/prime.py`, native bridge/catalog and upstream trees.
- **Parent:** integration verification, throwaway smoke evidence, docs/changelog and milestone reconciliation after proof. This hook writes only this AI-SPEC.

The planned new module/test paths are implementation-plan outputs, not claims that files already exist. [CONTRACT; SOURCE: phase plans' file ownership]

---

## 4. Implementation Guidance

**Model Configuration:** Retain the selected full Prime model descriptor, credentials/broker behavior, existing provider options, temperature/reasoning/context limits, and native metadata. This phase chooses no new model or sampling parameter. `max_iterations` and a caller-supplied `IterationBudget` remain the cumulative outer bounds across all tool/model/implicit-continuation rounds; the agent-created budget may refill only at the normal start of a new public turn. Add no continuation-round cap. [SOURCE: `runtime.py`, `providers/prime.py`, `agent/budget.py`; CONTRACT]

### Core Pattern: one loop, optional live boundary hooks

**Observed baseline flow:** `OmegaPrimeAgent.run` supplies its existing message list to `run_conversation`; that function acquires/releases the lease, opens substrate once, installs/reuses the system prompt, starts journaling, runs the existing interrupt/pause/budget/model/tool/text logic, finalizes once, and restores tool wrappers. Model tool schemas come from the same registry; dispatchers execute through `registry.dispatch`. [SOURCE: `runtime.py`, `conversation_loop.py`, `turn_tool_round.py`, `turn_final_response.py`, `turn_finalizer.py`]

**Required cutover:**

1. Enabled registrations publish only the three locked binding shapes. Disabled registration exposes no binding. `OmegaPrimeAgent` consumes these same resources through default-absent hooks. Nothing in a binding changes policy, approvals, roster selection, or credentials.
2. Capture successful-call usage immediately after each `model.complete`, including tool-call rounds. Keep the public-run aggregate separate from the uncharged usage for each logical text/stop boundary. A logical boundary is not a fresh public run and not each model call: do not repeatedly pass a growing aggregate into `accrue_turn`/`after_turn`, advance turn/stale counters per tool round, or charge it again at finalization.
3. Reload authoritative goal state and dereference the live autonomous holder at boundaries. Apply each logical-turn charge once before checking its next continuation, so a token limit is visible before another model call. Unknown usage contributes no fabricated tokens; unknown remains unknown/omitted in reported usage, with existing store arithmetic yielding zero.
4. If a later provider call raises, charge the unconsumed known usage from earlier successful calls before unwinding, without running a completion gate or requesting another continuation. Preserve the original exception type/propagation. Failure of a Prime accounting hook must not replace that exception. [CONTRACT]
5. Evaluate stop precedence before appending any continuation: explicit interrupt; failed/incomplete/ordinary refusal outcome; authoritative paused/completed/cleared/stale/exhausted goal; autonomous stop/quality-gate outcome. Either applicable stop wins over any other family's continuation request. An absent goal is not a veto on an independently enabled running driver. A removed/stopped driver cannot be resurrected from a cached reference.
6. Only an eligible boundary appends the existing goal/driver continuation as a user-role row and resumes the same loop. Preserve transcript prefix, raw `prime_message`, system prompt bytes, journal run, lease, pause/steer semantics, output limits, cumulative API-call count, and budget identity. Finalize the public run once.
7. Goal completion is read from a fresh store handle's state/report. There is no goal-complete tool in `GOAL_TOOL_NAMES`; a text response or all-done step list is not authorization to invent one. External completion regressions call `PrimeGoalStore.complete()` through another handle.
8. Use the real `AutonomousDriver.after_turn` and configured argv gate. Existing limit-first and sticky-stop behavior/note text remain honest: a passed gate proves only its command, and a limit never implies task success.

[CONTRACT; SOURCE: goal/autonomous methods, finalizer result shape, native usage/reset behavior]

**Native usage normalization:** `_usage` preserves valid integer counters and maps native `input/output/totalTokens/cacheRead/cacheWrite` into `prompt_tokens/completion_tokens/total_tokens/cache_read_tokens/cache_write_tokens`. Prompt tokens already include cache counters; total tokens are authoritative when supplied. Aggregate each key independently; never count total plus components or add cache counters a second time. When only prompt/completion counters exist, reuse `goal_token_delta_for_usage` semantics to determine the known token delta for budget consumption, without altering the raw native message. All actual `last_usage` shapes relevant here are dict or `None`; add no speculative dataclass-usage branch. [SOURCE: `providers/prime.py::_usage`, `agent/goals.py::goal_token_delta_for_usage`; CONTRACT]

### Tool Use

Keep current tool names, parameter schemas, approval flags and ordinary error rows. Goals use `goal_set/pause/resume/clear/status`; autonomy uses `autonomous_start/status/stop`; heartbeats use `heartbeat_set/list/clear`. Internal factories/holders are control attachments, not alternative dispatch paths. Approval/policy refusal must not be converted to a capability-degradation success or cause an automatic privileged retry. Quality gates use the existing configured argv/root/retry window; no shell-string inference or execution of gate output. [SOURCE: tool registrations, registry dispatch, driver gate; CONTRACT]

### State Management and Named Scheduling

- Reuse goal `goals.json` plus `prime_goal.json`, and the same per-registry autonomous holder. No second schema/state machine. [SOURCE; CONTRACT]
- One registry-bound `HeartbeatRuntime` owns the resolved `root/cron/jobs.json` path and the existing APScheduler convention. Enabled same-path re-registration reuses it. Named sessions share that registry/runtime, not a process singleton or cross-registry cache. [CONTRACT]
- The locked named interfaces are `bind(name, runner, *, event_sink=None)` and `unbind(name, *, runner=None)`. Capture a beat's runner/sink pair together; unknown names produce explicit errors, never a new conversation. Conditional unbind compares the expected runner atomically, so stale close cannot remove a replacement.
- The constructor's optional service sink receives undirected diagnostics only. Session-specific degradation belongs to the captured named sink, not the last constructed agent.
- Extend `SessionLease.acquire(*, wait=False)`: default foreground fast-fail remains; `wait=True` waits and takes ownership atomically. The heartbeat runner passes that opt-in through the real run path. `release()` wakes waiters. Do not hold a job/bookkeeping lock across lease waiting or model/tool callbacks. [CONTRACT; OFFICIAL: condition-object semantics]
- Claim/capture under bookkeeping synchronization, execute outside it, then reconcile completion into freshly read state. Clear during a callback must not resurrect the job; another schedule/update must not be overwritten by a stale save. Preserve the current 20-entry history convention and exclude foreign cron kinds. [CONTRACT; SOURCE: `cron/scheduler.py::HISTORY_LIMIT`, heartbeat kind]
- Start/restart reconciles current persisted entries, including removed/completed/no-longer-heartbeat entries; tools synchronize the live scheduler. Closing one binding keeps other live bindings running; closing the last owned binding stops scheduling. All-off construction starts no scheduler thread. [CONTRACT]
- Store the actual JSON-serializable callback result/response. A non-JSON result or ordinary callback failure becomes a structured error with redacted degradation evidence; never persist raw `repr`, invent a successful response, or corrupt the jobs file. No new callback cancellation/watchdog service is implied. [CONTRACT]

**Context Window Strategy:** Preserve the original system prompt/transcript and existing sanctioned compaction behavior. No prompt rebuild on continuation, new summarizer/RAG path, silent history truncation, or signature rewriting. The raw native `prime_message` must survive append/journal/JSON replay; visibly edited content with stale metadata must still fail replay explicitly. [SOURCE: loop comments, provider replay validation; CONTRACT]

---

## 4b. AI Systems Best Practices

### Structured Outputs with Pydantic

**Production applicability:** No Pydantic model migration, response-format API, validation retry, or new output dependency is required. The current loop returns dicts and the existing Prime connectors use their own typed views. Keep these boundaries. Pydantic 2.13.5 is already declared in `requirements-lock.txt`, but a transitive lock entry is not permission to add it to the product path. [SOURCE; CONTRACT]

The template's Pydantic example is a **read-only evaluation illustration**, not implementation code or an additional usage shape. It applies official strict validation to the known normalized fixture in `test_prime_provider.py::test_text_system_options_and_usage`; production accounting still uses the existing dict/`None` and token-delta helpers.

```python
from pydantic import TypeAdapter
from omega_prime.agent.goals import goal_token_delta_for_usage

known_usage = {
    "prompt_tokens": 16,
    "completion_tokens": 3,
    "total_tokens": 19,
    "cache_read_tokens": 4,
    "cache_write_tokens": 2,
}
validated = TypeAdapter(dict[str, int]).validate_python(known_usage, strict=True)
assert goal_token_delta_for_usage(validated) == 19
```

[OFFICIAL: [Pydantic strict mode/type-adapter validation](https://docs.pydantic.dev/latest/concepts/strict_mode/); SOURCE: fixture and lock. Example not executed here.] Strict validation is an oracle illustration, not a reason to throw on formerly unknown usage or retry a billed model call.

### Async-First Design

The actual loop/provider interface is synchronous, with background APScheduler threads for scheduling. Do not introduce `asyncio`, async SDKs, process workers, or a second loop to satisfy this generic template heading. Concurrency correctness here is atomic lease ownership, short bookkeeping critical sections, and lifecycle settlement. Awaiting/streaming decisions remain owned by the existing native completion adapter. [SOURCE; CONTRACT]

### Prompt Engineering Discipline

Reuse the stored objective/next-step and driver's existing continuation prompt. Add them only as user-role continuation rows after precedence checks. Model/tool text cannot elevate authority, approve writes, or declare stored goal completion. Preserve the initial system prompt and live registry schemas. No prompt optimization or few-shot experiment is requested. [SOURCE; CONTRACT]

### Context Window Management

Retain the same message list and native wire metadata through foreground/implicit/scheduled turns. Existing compaction is the sanctioned history-rewrite mechanism; this phase introduces none. Test history content and order, not just binding existence. [SOURCE: loop invariants and provider metadata validation; CONTRACT]

### Cost and Latency Budget

No per-call dollar estimate, p95 claim, cache strategy, or sub-task model routing is justified by the inputs. Known token usage and configured goal/autonomy limits are the cost controls; missing usage cannot be priced or estimated. The existing cumulative model-call cap/iteration budget bounds even unknown-usage continuation. Retain provider timeouts and autonomous minute/gate timeout settings. Test deadlines are hang detectors, not service latency SLOs. No new round cap or arbitrary timeout mechanism is authorized. [CONTRACT; INFERENCE]

---

## 5. Evaluation Strategy

### Dimensions

All correctness dimensions are **pass/fail**, using code assertions on consumer-visible behavior. No LLM judge, synthetic reasoning score, benchmark comparison, or majority-vote success criterion is needed for deterministic internal boundaries. Human review interprets smoke evidence and honest outcome wording. [SOURCE: existing structural eval runner; INFERENCE]

| Dimension | Pass rubric; fail condition | Measurement approach | Priority |
|---|---|---|---|
| Actual usage | Each known successful call is counted exactly once; mixed/tool/cache usage and success-before-failure totals match fixtures; unknown usage is not fabricated. Fail on final-call-only, duplicate, or lost charging | Real agent/store/driver assertions, provider mapping regression, native HTTP requests | Critical |
| Continuation precedence | Applicable stop state wins; no extra call after interrupt/incomplete/refusal/goal/driver stop; holder removal stays removed. Fail on any automatic re-entry overriding a stop | Parameterized deterministic boundary cases | Critical |
| Cumulative bounds | Total calls never exceed the existing cap or caller budget; tool rounds are not autonomous turns; no budget refill or second round cap. Fail on extra call/refill/per-call turn increment | Call count plus real budget/driver/store counters | Critical |
| Honest stops/completion | Preserve exact limit/gate reason and scope note; completed goal is external-store driven; exhausted budget does not mark objective completed. Fail on false success or invented complete tool | Real argv gates, fresh-store report and result inspection | Critical |
| Failure containment | Hook failure emits structured redacted evidence and cannot extend continuation; provider/BaseException propagation survives; JSON beat failure remains an error. Fail on swallowed exception, secret, hang or `repr` success | Failure injection at the actual boundary | Critical |
| Named overlap/ownership | Target history only, foreground exclusion and atomic heartbeat wait, independent sinks, replacement survives stale close. Fail on transcript interleaving, cross-routing or lock deadlock | Deterministic barriers and real lease/runtime/agents; parent scheduler smoke | Critical |
| Durable scheduling | Correct actual result/history, bounded history, no duplicate due execution, no lost update/resurrection, restart reconciliation, foreign jobs untouched. Fail on disk/scheduler divergence | Reloaded jobs JSON plus current scheduler entries | Critical |
| Flags-off/messaging parity | Original prompt/transcript/tool/error behavior and messaging preserved, no Prime runtime activity or new scheduler threads. Fail on any unauthorized off-path change | Unmodified neighbors plus exact flags-off transcript comparison | Critical |

The assembled prompt is currently an allowed tool superset; live offered schemas are authoritative (`docs/agent-loop.md`, `README.md`). Flags-off parity must not invent a new static prompt-pruning convention. Assert disabled live tools/bindings and absence of enabled-only runtime rows/events while retaining pre-v10 system-prompt bytes. [SOURCE; CONTRACT]

### Eval Tooling

**Primary Tool:** Existing `.venv/bin/python -m pytest` behavior regressions, with `omega_prime.evals.runner` as the existing structural compatibility/red-team gate. Reuse `ScriptedModel` for deterministic call sequences, real on-disk stores, real driver/gate argv, and real registry dispatch. Clock/barrier controls isolate timing; canned hook verdicts or binding-exists assertions are not sufficient integration evidence.

**Tracing/eval default override:** Retain existing harness events, optional tracer/journal and job history. Do not install Arize Phoenix, Langfuse, Promptfoo, a judge SDK, or another eval service merely because a generic GSD reference suggests it. The phase requires no new dependency or observability infrastructure. [CONTRACT; SOURCE]

**Setup:** Parent uses the existing Python environment and sandbox HOME/XDG conventions. `tests/conftest.py` isolates PyRIT's data directory through `XDG_DATA_HOME`; do not import it before that isolation or direct tests into the operator's real data. No installer is run by this hook.

**CI/CD integration and parent commands:** These are commands for the parent **after both units land**, not executed results. The first two test files are planned outputs of 61-01/02. Keep commands genuinely runnable in each plan's `<automated>` field (no `PARENT-RUN` command prefix), explain parent ownership in prose, and attach a meaningful `<fails_when>` for every task. A selector that collects zero intended tests is not proof.

```bash
.venv/bin/python -m pytest omega_prime/tests/test_prime_loop.py omega_prime/tests/test_heartbeat_runtime.py -q
.venv/bin/python -m pytest omega_prime/tests/test_loop.py omega_prime/tests/test_durable.py omega_prime/tests/test_goals_prime.py omega_prime/tests/test_autonomous.py omega_prime/tests/test_prime_contracts.py omega_prime/tests/test_prime_degraded.py omega_prime/tests/test_prime_failure_injection.py omega_prime/tests/test_heartbeat.py omega_prime/tests/test_apscheduler_backend.py omega_prime/tests/test_prime_provider.py omega_prime/tests/test_prime_config.py omega_prime/tests/test_prime_regression.py omega_prime/tests/test_agent_message.py -q
.venv/bin/python -m pytest omega_prime/tests/test_prime_runtime_e2e.py -q -rs
.venv/bin/python -m pytest omega_prime/tests -q
.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases
bash omega_prime/scripts/assemble-prompts.sh --check
.venv/bin/python -m omega_prime.setup_check --root .
```

Parent also owns Ruff/mypy/format-check and prompt/catalog verification per Context/repository configuration. This spec changes no CI file. The current structural eval runner constructs `Agent` or generic registry cases and does not establish the new Prime hook/named scheduler integration by itself; the focused production-boundary tests and smoke below supply that evidence. No Rust source changes are in scope; do not rerun the documented upstream ext4 failures to reconfirm them. [SOURCE: `evals/runner.py`, `CONTRIBUTING.md`; CONTRACT]

### Reference Dataset

**Size:** 16 explicitly labeled scenario groups, with parameterized variants as listed; this is a test/evidence specification, not a claim that 16 new fixtures already exist or passed. Reuse existing regression examples instead of adding a separate dataset framework.

| ID | Input/setup and expected behavior | Explicit failure direction |
|---|---|---|
| E01 | Dispatch `goal_set` with objective and unfinished step through a real approved registry, then run a real agent with two eligible text boundaries; appended continuation shares transcript/prompt/lease/journal | No second call from live state, fresh agent/run, changed prefix, or extra finalization |
| E02 | External fresh store handle pauses/completes/clears the goal between boundaries; resume is tested on a later eligible turn; completion report is loaded from stored completion | Cached goal ignores update, completion is inferred from text, or a nonexistent complete tool is used |
| E03 | A goal with token budget 10 receives two successful text calls of 7 tokens, then stops with persisted 14; no-usage logical turns exercise the existing stale threshold | Persisted 0/7/21, call after exhaustion, or stale counter increments per tool round |
| E04 | Tool-model rounds contribute known usage, including the native normalized 19-token/cache fixture; consume one logical-turn delta, not each counter as separate token cost | Tool usage lost, cache counted twice, total+components counted together |
| E05 | Successful known-usage tool call followed by real `ProviderError`; reload goal/read driver accounting after the raised call | Prior usage erased, charged twice, or original provider exception becomes degradation-only result |
| E06 | Current provider dict/`None` shapes, prompt/completion-only usage, and malformed counters from existing mapping tests | Estimated usage, bool/string/negative claimed as tokens, stale last usage reused, speculative usage-object branch |
| E07 | Real started driver with `max_turns=2`; text boundaries advance turns while intervening tool rounds do not | Registered holder ignored (parent baseline), per-model turn increment, or restarted stop |
| E08 | Real driver token/minute limits and real `/bin/true` / `/bin/false` gates with existing retry window | Limit claims success, gate scope note lost, extra continuation after either gate stop, or gate runs on incomplete turn |
| E09 | Parameterize interrupt, incomplete/empty result, outer cap, exhausted caller budget, paused/completed/cleared/stale/exhausted goal, sticky/removed driver, and competing continuation requests | Any stop overridden, refilled budget, new round cap, or original user/refusal outcome replaced |
| E10 | Failing Prime goal/autonomy hook, raised timeout exception, invalid hook payload and fake credential; control exceptions tested separately | Unredacted/missing event, provider/KeyboardInterrupt/SystemExit swallowed, failure-enabled continuation or hang |
| E11 | Two named live agents use the same authoritative registry/runtime; beat sees the correct prior transcript and routes errors to its captured sink; unknown target is explicit error | Fresh conversation, wrong history/sink, or unknown target succeeds |
| E12 | Foreground turn holds the real lease; heartbeat waits atomically while foreground heartbeat set/list/clear dispatch remains usable; foreground overlap still fast-fails | Concurrent transcript access, check-then-act acquisition, default wait change, deadlock under bounded test deadline |
| E13 | Replace a named binding, then close old agent; close one of several bindings, then last; same-path re-registration | Replacement detached, surviving session scheduler stopped, duplicate runtime or leaked owned scheduling |
| E14 | Callback result/error/non-JSON value is exercised through the heartbeat runtime; reload actual JSON history and run more than 20 ticks deterministically | `repr` success, secret in error evidence, corrupt/unbounded history, duplicate same-due execution |
| E15 | Schedule/clear during an active callback, modify persisted entries while stopped, restart/double-start; include foreign cron kind and changed/completed heartbeat | Cleared job resurrected, new job overwritten, stale scheduler entry survives, foreign job runs through heartbeat |
| E16 | All flags off through production composition; compare existing transcript/system prompt/offered tools/events/thread lifecycle; preserve existing two-session messaging suite | New runtime rows/tools/bindings/threads, altered fast-fail/refusal behavior, or modified messaging expectations |

**Labeling:** Loop/scheduler maintainers label inputs and exact expected counts/state/reasons using the inspected methods; parent reviews the externally visible results and persists command/exit-code evidence. There is no LLM-generated ground truth or uncalibrated judge. No exact performance figure is inferred from these labels.

### Parent Native HTTP and Real Scheduler Smoke

These are mandatory complementary integration experiments, not new provider/API coverage or committed harness scaffolding. Parent runs them after deterministic regressions and owns any throwaway fixture cleanup/evidence.

1. **Native HTTP:** Reuse the localhost streaming-peer pattern in `test_prime_runtime_e2e.py` with the real loaded extension, `OmegaPrimeAgent.from_prime`, real registry dispatch and disk-reading tool. Keep the existing descriptor/API. In an enabled-goal variant, use an unfinished goal and known 12-token-per-call peer responses with budget 36: tool call + text + implicit text continuation must yield three real HTTP model calls and goal usage 36, not final `last_usage` 12. Preserve prior/tool/native metadata through JSON replay; retain the existing approval-refusal and timeout/error behaviors. An independently enabled autonomy variant proves the real native loop consults its registered holder. Inspect actual counts/reasons rather than relying on emitted text as proof. [SOURCE: existing peer and tests; CONTRACT: enabled-boundary smoke; INFERENCE: fixture arithmetic]
2. **Real scheduler:** Construct named live agents sharing one registry-bound runtime and persisted jobs path; schedule through actual `registry.dispatch`. With real APScheduler firing during an in-flight foreground turn, prove the target waits on the real lease, foreground heartbeat tools remain usable, and only the target's original transcript receives the beat after release. Reload on-disk history to match the actual callback result/error. Exercise per-binding sink routing, replacement/stale-close ownership, and closure of the last binding. A direct helper tick or recorder-only scheduler callback is insufficient to prove production re-entry. [CONTRACT]
3. **Evidence record:** Parent captures commands and exit codes, collected/exercised case identities, actual model-call and persisted-token counts, stop/gate reasons, redacted owning-session events, request/metadata checks, disk history and scheduler/lifecycle observations. Note native skips, zero-selection, and missing prerequisites explicitly. Existing native/scheduler test definitions are baselines, not results of this hook.

The native extension and working existing environment are future smoke prerequisites; their availability was not checked by running code here. No live-service credentials are required for the localhost HTTP parser smoke. No prerequisite blocker to writing this advisory contract was found.

---

## 6. Guardrails

### Online (Real-Time)

These are existing controls to preserve or locked boundary behavior to implement, not newly installed services.

| Guardrail | Trigger | Intervention |
|---|---|---|
| Cumulative model/iteration bound | Existing cap/budget spent | No extra model call; retain honest stop outcome, without refill or another round cap |
| Authoritative goal/driver stop | Paused/completed/cleared/stale/exhausted goal or autonomous stop/gate verdict | Suppress implicit continuation; preserve report/reason and stopped state |
| Interrupt/incomplete/failure/refusal precedence | User interrupt, failed/incomplete boundary, ordinary policy/approval refusal | Preserve original handling; do not gate/retry/escalate privileges through a Prime hook |
| Registry authority | Model attempts a tool call | Existing policy/approval/roster dispatch path; internal bindings grant no tools |
| Guarded Prime hook | Hook raises or rejects payload | Structured redacted `prime_degraded`; no continuation from failed hook; provider/control exceptions remain outside containment |
| Exclusive named session | Scheduled re-entry overlaps foreground ownership | Atomic opt-in lease wait outside job locks; no fresh/wrong session fallback |
| Binding ownership | Agent closes after replacement | Atomic expected-runner unbind; other live bindings and their sinks retain ownership |
| Durable result integrity | Runner error or non-JSON result | Explicit structured error/redacted degradation, no raw `repr` success or jobs-file corruption |

[CONTRACT; SOURCE: existing guards and failure paths]

### Offline (Flywheel)

| Metric/evidence | Sampling strategy | Action on degradation |
|---|---|---|
| Usage/count/state mismatch | Every deterministic boundary case and native HTTP smoke | Fail acceptance; fix arithmetic at the owning boundary, never estimate missing usage |
| Extra continuation/false success | Every precedence, cap, gate and completion case | Fail acceptance; preserve exact source semantics and stop evidence |
| Session/history/lifecycle mismatch | All overlap/rebind/lost-update cases and real scheduler smoke | Fail acceptance; repair ownership/lock/update boundary, not retry into a fresh session |
| Flags-off difference or new thread | Exact baseline parity and unmodified neighboring suites | Reject enabled-feature spillover; do not rewrite baseline to fit the new behavior |
| Missing/skipped evidence | Every named acceptance command/scenario | Leave requirement pending; parent records the prerequisite rather than claiming a pass |

No new production sampling pipeline or telemetry dependency is authorized. [CONTRACT]

---

## 7. Production Monitoring

**Tracing Tool:** Existing `agent.harness.emit/events_of` for structured redacted events; existing optional agent tracer/journal; persisted JobStore history for beats. Keep these hooks and their owning-session attribution. Do not configure Arize Phoenix or another service. Current source provides the observation mechanisms; this advisory document does not claim any production dashboard, alert, or monitoring deployment. [SOURCE; CONTRACT]

**Key Metrics/Observations to Track:**

1. Actual successful-call usage versus persisted goal/driver deltas and cumulative model-call count.
2. Original `turn_exit_reason`, autonomous verdict/note and goal completion state, separate from text-response completion.
3. `prime_degraded` family/error/turn identity and captured session owner, with redaction.
4. Persisted heartbeat result/history/due time/claim state versus live scheduler entries and foreground/beat ordering.
5. Live binding ownership and owned scheduler thread settlement; zero new scheduling activity with flags off.

These are observable acceptance data using existing surfaces, not promises of new metric instrumentation. [SOURCE; INFERENCE]

**Alert Thresholds:** No paging policy or latency/error-rate threshold is supplied. For phase acceptance, any deterministic critical-rubric violation, unredacted secret, wrong-session delivery, false success, budget overrun, corrupt history, deadlock, or native-smoke skip is a failure/missing-evidence condition. Test wait deadlines indicate a potential hang and do not establish an SLO. Parent decides operational incident/escalation policy outside this artifact. [CONTRACT; INFERENCE]

**Smart Sampling Strategy:** Parent inspects all failure-injection, stop/gate, overlap/replacement and unknown/non-JSON cases, plus the complete native HTTP and real scheduler smoke traces. For existing runtime diagnostics, prioritize already available degradation/stop/history records; introduce no new retention, content collection, or continuous telemetry work in this phase. [CONTRACT]

---

## Checklist

Checked items denote completed **design content**, not implementation or gate results.

- [x] System type and existing production flow classified.
- [x] Five critical failure modes tied to operator-visible consequences.
- [x] Domain good/bad/stakes rubric and source provenance defined.
- [x] Applicable repository constraints identified; no sector-compliance claim invented.
- [x] Evaluation roles defined without claiming unavailable specialists ran.
- [x] Locked existing framework/provider/version recorded; exclusions are not new implementation alternatives.
- [x] Quick reference includes existing imports, real entry-point syntax, pitfalls and disjoint ownership.
- [x] Structured-output applicability, strict Pydantic illustration, synchronous concurrency, prompt/context and budget guidance specified without product changes.
- [x] Actual usage, precedence, honest stops, failure containment, named overlap/history and flags-off parity have explicit pass/fail rubrics.
- [x] Existing pytest/structural eval/event tooling selected; generic tracing default explicitly overridden.
- [x] Sixteen scenario groups and their failure directions/labeling defined.
- [x] Runnable parent commands and evidence requirements specified; no verification executed here.
- [x] Parent native HTTP and real APScheduler smoke defined independently of helper/wiring tests.
- [x] Online/offline guardrails and existing-surface observation contract specified; no monitoring configuration claimed.

**Readiness:** Advisory design contract complete. Implementation and all verification remain parent/assigned-unit work. No genuine input blocker to this artifact; runtime smoke prerequisites and their pending verification are stated above. No requirement, milestone, security gate, performance gate, or release is marked passed by this document.
