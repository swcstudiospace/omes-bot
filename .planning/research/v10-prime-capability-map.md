# v10 Prime Agent capability map

**Produced:** 2026-10-08 · Phase 53 (Prime discovery + parity baseline)
**Tracker:** SPE-8002 / SPE-8004
**Source:** `prime-agent/` @ `967eb13fd488507af5f590e9c6ea8b2672f1fc05` (MIT, PrimeIntellect) — read-only checkout
**Architecture decision:** behavior-port into `omega_prime/` Python; Rust workspace is the CI-built parity oracle; connectors are typed Python adapters.

Every claim below cites the file it was read from. `rlm/…` paths are under
`prime-agent/prime-agent-runtime/src/rlm/`; `pa-*` paths under
`prime-agent/crates/`.

---

## 1. RLM recursion surface (spawn / collect / list / delete / create_session / progress_note)

**The core "powerful logic":** the model drives recursion programmatically —
from inside a persistent Python REPL it spawns real child agents, collects
their typed results, and inspects/reaps them, all through one kernel API.

- **Source:** `rlm/__init__.py` (kernel-side API), host side in
  `pa-core/src/session_engine/` (`rlm_host` seam) + `pa-daemon` worker/supervisor.
- **Public API (verbatim signatures, `rlm/__init__.py`):**
  - `async def spawn(prompt: str, *, name: str, model: str | None = None, thinking: str | None = None) -> RLMSpawnHandle` (line ~170) — wire type stays `"rlm.run"` for cross-version compat (comment line 191). `name` required, unique among siblings. Returns `RLMSpawnHandle(rlm_child_id, name, session_dir: Path, model)` (line ~28).
  - `async def collect(targets: Any = None, *, timeout_ms: int = 0) -> list[RLMChildResult]` (line ~399) — targets: handle, subagent row, name string, or mixed list; `None`/empty selects all direct children not being deleted. `timeout_ms=0` is a non-blocking snapshot; a positive value blocks only this call; **a timeout returns current snapshots, never an error, and the parent is never steered** (docstring lines 410-417). Completed children keep results until deleted.
  - `async def list_subagents() -> list[RLMSubagent]` (line ~330) — direct children retained by the current parent. `RLMSubagent` fields: `rlm_child_id, active_session_id, session_id, session_name, session_dir, status, activity, tool_use_count, duration_ms, answer_preview, replied_since_task, progress_note, label, last_activity_at, activity_stale_ms` (lines ~49-73).
  - `async def delete_subagent(...)` — reaps a child and drops its retained result (payload-validated like the others).
  - `async def create_session(prompt, name=None, model=None, thinking=None, cwd=None) -> RLMCreateSessionHandle` (line ~209) — **only daemon-backed depth-0 sessions** support it; returns `RLMCreateSessionHandle(active_session_id, session_id, name, session_file: Path, model)`.
  - `async def progress_note(message: str) -> RLMProgressNoteResult` (line ~439) — max 512 UTF-16 code units (`RLM_PROGRESS_NOTE_MAX_LENGTH = 512`, line 436), ~1 per 10s throttle; a throttled note returns `accepted=False` + `retry_after_ms`, **never raises** (lines 440-447).
  - `async def find_models(query: str = "", limit: int = 8) -> list[RLMModel]` (line ~237).
- **Must-preserve behaviors:**
  - Status vocabularies are closed sets, validated on decode: subagent `status ∈ {running, completed, error}` (`__init__.py:309`); collect `status ∈ {queued, running, done, error, cancelled}` (`__init__.py:358`); activity `kind ∈ {waiting, writing, executing}` (`__init__.py:281`).
  - Every payload field is type-checked on decode with `RuntimeError` on malformed host replies (`_spawn_handle_from_payload`, `_subagent_from_payload`, `_child_result_from_payload` — lines 87-395). Bool/int confusion is rejected explicitly (`isinstance(value, int) or isinstance(value, bool)` guards, e.g. lines 260, 375).
  - Error channel: host replies `{status: "ok"|"error"}`; `"error"` raises `RuntimeError(error)`; any other status raises "unexpected status" (`_parse_host_reply`, lines 134-142).
  - Collect timeout semantics: partial snapshots on timeout, never an exception (docstring 410-417).
- **Omega merge target:** extend `omega_prime/agent/delegate.py` (already has isolated children + background handles) with an RLM-shaped tool family `omega_prime/tools/rlm.py`; parent/child registry state lives in-process (Omega Prime is single-process — no daemon needed).
- **Overlap:** `delegate_task` (one child per goal, `background=True` handle, `join_delegate`) is the subset Prime generalizes to N named children with inspect/reap/progress. Port keeps `delegate_task` untouched; RLM tools sit beside it.

## 2. Persistent REPL semantics

- **Source:** `rlm/repl.py` — "Minimal CPython REPL runtime speaking newline-delimited JSON over stdio" (module docstring). Entry: `python -m rlm.repl`.
- **Key facts:** `PROTOCOL_VERSION = 3` (line 36); cells execute with top-level await in **one persistent `__main__` namespace on a single asyncio event loop**; host bridge `async def host_request(data)` (line 173); payload cap `_PAYLOAD_CAP` with JSON framing split at 16_384 bytes (lines 1440-1460); state snapshots via dill with v2 framed format sniffed by magic `_SNAPSHOT_MAGIC = b"PRIME-AGENT-KERNEL-SNAPSHOT-V2\n"` (line 43), defaults `DEFAULT_SNAPSHOT_MAX_BYTES = 256 MiB`, per-variable 16 MiB (lines 38-39); stdout/stderr are replaced with cell-id-tagging writers (line 330); host closing stdin without a shutdown request shuts the runtime down (lines 1387, 1591).
- **Must-preserve:** one persistent namespace across cells; top-level await; NDJSON framing; snapshot size guards; stdin-EOF = shutdown.
- **Omega merge target:** Omega Prime already executes code via `execute_code` (v1 Phase 6). The port adds an *opt-in persistent namespace* mode to code execution (a session-scoped namespace dict) rather than a separate kernel process — same semantics, in-process. NDJSON stdio framing is NOT ported (no second process).
- **Overlap:** `tools/execute.py` exists; gap is persistence + top-level await + snapshot guards.

## 3. Continual harness + `/refine`

**The second pillar:** durable supplemental state the agent refines with small, evidence-backed updates.

- **Source:** `rlm/harness.py` (kernel-side state), `pa-core/src/refinement/` (`planner.rs`, `executor.rs`, `ranking.rs`), trigger scheduling in `pa-daemon/src/compact_autorefine.rs`.
- **State model (`rlm/harness.py`):** `HarnessKind = Literal["prompt", "memory", "skill", "subagent", "factory"]` (line 33); `HarnessScope = Literal["local", "global"]` (line 34) — **session-local by default, `global_=True` for cross-session** (module docstring). Store file `harness_state.json` under a `harness/` dir (lines 36-37). `HarnessEntry` (line 184), `RefinementEvent` (line 203).
- **API:** `HarnessState` (line 389) with `load`/`save`/`upsert`/`get`/`delete`/`list`/`create` (lines 524-817); per-process lock-dir with stale-owner reclaim (`_LOCK_STALE_AFTER = 10.0`, 50 attempts × 20ms, lines 40-42, `_acquire_lock_dir` line 473); disk-mtime sync for cross-process visibility (`_sync_from_disk`, line 435).
- **Validation:** strict entry-shape validation per kind (`_validate_entry_shape`, line 312); refinement events require trigger/changes/evidence/outcome (`_validate_refinement_event`, line 369) — **evidence is mandatory**, matching the "evidence-backed updates only" rule; Python-skill references validated (`_validate_python_skill_reference`, line 218); factory specs validated (`_validate_factory_arguments`, line 290).
- **Must-preserve:** local-default scoping; evidence-required refinement events; entry-shape validation; snapshots before mutation (refinement history enables rollback — recorded in `RefinementEvent` log); the base system prompt is immutable (per Prime README: refine "never rewrites the immutable base system prompt").
- **Omega merge target:** extend `omega_prime/agent/curator.py` (post-turn curator already decides when a turn earned a skill) + new `omega_prime/learning/harness.py` for the state store. Refine trigger becomes a rostered tool + routine.
- **Overlap:** curator writes skills only; harness generalizes to prompt/memory/skill/subagent/factory kinds with global scope and rollback.

## 4. Goals engine

- **Source:** `pa-core/src/goals.rs` (+ `pa-types::goal` wire state; daemon `goal_continuation.rs`, `goal_state_persist.rs`).
- **API surface:** `validate_goal_objective` (line 108), `validate_goal_budget` (line 126), `goal_token_delta_for_usage` (line 136), `stale_active_goal_failure` (line 143), `normalize_goal_state` (line 86), `goal_update_dedupe_projection` (line 77), `create_goal_context_message` (line 271), `format_goal_usage` (line 298). `GoalContextKind` enum (line 17), `SerializedGoal` (line 36).
- **Semantics:** a persistent thread goal with an objective + optional token budget; usage accrues per turn; goal continuation runs at turn boundaries (daemon `goal_continuation.rs`); stale-active detection from session file entries; completion report on finish.
- **Omega merge target:** `omega_prime/learning/goals.py` already ports Omp goals (objective + steps). v10 extends it with budget accounting + continuation prompts at turn boundaries.
- **Overlap:** Omp goals = objective/steps; Prime goals = persistence + token budget + auto-continuation. Merge into one goals module satisfying both.

## 5. Heartbeats + schedules

- **Source:** `pa-core/src/cron/` (`scheduler.rs`, `store/` — `heartbeat.rs`, `jobs.rs`, `session_artifacts.rs` per crate README); skill `prime-agent/skills/rlm-heartbeat/SKILL.md`.
- **Semantics:** file-backed job state under session artifacts (`scheduled-jobs.json` partitions) with cross-process locking; heartbeats re-enter a session periodically; boot re-arm reads the roster projection (pa-core README).
- **Omega merge target:** `omega_prime/cron/` (scheduler + JobStore already exist, v1 Phase 5 + v4 APScheduler backend). Port the *session re-entry* job kind (heartbeat) and the artifact scan.
- **Overlap:** Omega cron fires routines; Prime heartbeats re-enter a specific session with a prompt. Small extension, new job kind.

## 6. Autonomous mode (budgets + quality gates)

- **Source:** `pa-core/src/autonomous/` (`mod.rs`, `driver.rs`, `gates.rs`); continuation wiring in `pa-daemon/src/autonomous_continuation.rs` and `pa-cli/src/print_autonomous.rs`.
- **Semantics (per pa-core README + AGENTS.md):** runtime state with limit normalization (turn/token/time budgets); continuation and gate-failure texts; **shell quality gates with retry windows and git worktree snapshotting**; `AutonomousDriver` policy trait consulted after every settled turn; the engine holds no autonomous logic of its own (host drives). A passed gate checks only what that gate verifies; reaching a limit does not imply task success (Prime README).
- **Omega merge target:** new `omega_prime/agent/autonomous.py` as a loop-adjacent driver consulted at turn finalization (`turn_finalizer.py` seam); gates run through existing exec/terminal tools; budgets reuse `agent/budget.py`.
- **Overlap:** Omega has iteration budgets; Prime adds multi-dimensional budgets + gates + continuation policy.

## 7. Agent-to-agent messaging

- **Source:** `pa-daemon/src/agent_messaging.rs` + `agent_messaging/` (`message.rs`, `observe.rs`), `agent_message_broadcast.rs`, `agent_message_ingest.rs`, `agent_roster.rs`; skills `agent-message`, `agent-observe`.
- **Semantics (per pa-daemon README):** the family view joins the supervisor roster with the session's RLM children registry — registry children are Child members addressable by name / RLM child id / persisted session id; the spawning session is Parent; everything else is a sibling. Delivery tries the direct peer transport, then supervisor-routed `send_message` as the never-retried fallback. Worker-to-worker grants are single-use with 10s TTL.
- **Omega merge target:** new `omega_prime/tools/agent_message.py` + a session registry (in-process; Omega sessions already persist via `session/persist.py`). Single-process: delivery is direct in-registry; the "supervisor fallback" collapses away.
- **Overlap:** none existing — this is net-new for Omega Prime.

## 8. Compaction

- **Source:** `pa-core/src/session_engine/` (compaction arms), `pa-daemon/src/compaction*.rs` (5 modules: supervision, outcome, auto), `pa-cli/src/print_boundary.rs` (turn-boundary checks: overflow compact-and-retry, model-requested compaction, threshold arm).
- **Semantics:** multiple compaction arms (overflow retry, model-requested, threshold) consumed at quiescent turn boundaries; compaction-entry fold for compacted reads; auto-refine can be scheduled after compaction.
- **Omega merge target:** `omega_prime/agent/compression.py` already implements "compression is the only rewrite of prior context" (LOOP-04, v1). Port the *arm vocabulary* (overflow/model-requested/threshold) as named paths.
- **Overlap:** high — Omega compression covers the core invariant; Prime adds the arm taxonomy + auto-refine hook.

## 9. Executable skills (Python packages)

- **Source:** `rlm/skill.py`, `prime-agent/skills/` (13 skills: agent-message, agent-observe, attach-image, compact, edit, factory, goal, mcp, prime-intellect, refine, rlm-heartbeat, skill-creator, websearch), `pa-core/src/skills/`.
- **Semantics:** skills are importable Python packages (not just markdown); a skill creator turns recurring workflows into project/personal skills; markdown skills carry the usage contract.
- **Omega merge target:** `omega_prime/skills_runtime/` + `tools/` skill manager (v1 Phase 4: create/edit/patch with frontmatter guards, 60-char description limit). Port: Python-package skills (importable) beside markdown skills.
- **Overlap:** Omega skills are markdown + manager; Prime adds executable Python skills.

## 10. Daemon supervision + session persistence

- **Source:** `pa-daemon/src/` (supervisor, `descriptor.rs`, `boot_reap.rs`, session store, archiving); session layout append-only JSONL (`~/.prime/agent/sessions`).
- **Semantics:** one worker process per active session; restart with backoff; workers re-register after supervisor restart; parent-death child cleanup; sessions persist append-only so reattach works; archiving by age (30d) and count (200), each rule off-able; resident/active sessions never archived.
- **Omega merge target:** NOT ported as a process model (one-Python-process rule). The *persistence* semantics map onto `omega_prime/durable/journal.py` (SQLite turn journal) + `session/persist.py`. Port: append-only session JSONL layout + archive-by-age/count as a maintenance routine.
- **Overlap:** durable journal covers crash resume; Prime adds the JSONL session format + archiving policy.

## 11. System-prompt layering

- **Source:** `pa-core/src/prompts/` (`layers/`, `layers.rs`, `system_prompt.rs`); AGENTS.md surface contract.
- **Semantics:** cache-stable static layer files (core harness description with full API surface, mandatory usage rules, opinionated guidelines, per-model map) followed by one dynamic tail (packages, project context, skills inventory, MCP servers, environment, session role); the harness digest is a separate `[harness-digest]` user message; `prime-agent prompt` dumps the assembled prompt with layer breakdown.
- **Omega merge target:** `omega_prime/assemble.py` + `prompts/` already do deterministic layered assembly (v1 SHELL-02: byte-stable). Port: the `[harness-digest]` separate user message + layer-breakdown dump command.
- **Overlap:** high; Omega's assembler is the base.

## 12. Factory workflows (state machines of spawned children)

- **Source:** `rlm/factory.py` (4,729 lines — the largest kernel module): `graph_factory`, `run_factory`, `resume_factory`, `status_factory`, `stop_factory`, `watch_factory`, `FACTORY_HELP`; validation in `harness.py` (`_validate_factory_arguments`, `validate_factory_spec`); skill `factory`: "Run state-machine workflows of spawned child agents: store a validated machine…".
- **Semantics:** durable state-machine workflows whose nodes are spawned RLM children; resumable, watchable, stoppable; specs stored as harness `factory` entries.
- **Omega merge target:** `omega_prime/durable/workflows.py` already has checkpointed workflows (v2). Factory = workflows whose steps are RLM children. Port after RLM tools land (Phase 55 dependency); candidate to scope down to the validated-spec + run/resume/stop core.
- **Overlap:** durable workflows provide the checkpoint spine; factory adds child-agent nodes.

---

## Config surface (Prime)

Settings keys observed in crate READMEs/source: `mcpServers`, `sessionArchiveMaxAgeDays` (default 30), `sessionArchiveMaxSessions` (default 200), telemetry opt-out precedence `PI_OFFLINE` / `DO_NOT_TRACK` / `PRIME_AGENT_TELEMETRY` / settings (pa-telemetry README), per-model thinking levels, autonomous budgets (turn/token/time) + gate commands. Wire-compat env: `PI_PACKAGE_DIR` (kept byte-compat per branding exception).

## Test surface (parity baseline sources)

- Rust: per-crate `tests/` + `#[cfg(test)]` modules — `cargo test --workspace` (baseline recorded in 53-01-SUMMARY).
- Kernel Python: `prime-agent/prime-agent-runtime/test/` (uv project, dev dep `dill`).
- Parity fixtures: `crates/pa-models/tests/fixtures/catalog.v1.json` pattern (generated fixtures) is the model for v10 connector parity fixtures.

## Unknowns (not confirmed from source)

1. Exact wire frames between pa-core kernel manager and the REPL beyond NDJSON + protocol v3 (`repl.md` beside `repl.py` documents it; not yet read line-by-line — read in Phase 55 if the port needs frame-level detail).
2. `rlm.delete_subagent` exact payload shape (validation mirrors the others; signature line not captured verbatim).
3. Prime's per-provider error taxonomy (pa-ai) — out of v10 scope (Omega keeps its own providers), noted so it isn't silently dropped from future consideration.
4. Factory spec schema details (4.7k-line module; Phase 55+ will read it when porting the factory core).
