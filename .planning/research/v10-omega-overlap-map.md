# v10 Omega Prime overlap map

**Produced:** 2026-10-08 · Phase 53 (Prime discovery + parity baseline)
**Tracker:** SPE-8004
**Purpose:** where each ported Prime capability plugs into the existing
Omega Prime codebase. Companion to `v10-prime-capability-map.md`.

---

## 1. Module inventory (non-test, `__pycache__` excluded; 24,364 lines total)

| Area | Modules (lines) |
|---|---|
| Loop core | `agent/conversation_loop.py` (452), `agent/turn_tool_round.py`, `agent/turn_final_response.py`, `agent/turn_finalizer.py`, `agent/prompt_builder.py`, `agent/budget.py`, `agent/compression.py`, `agent/interrupt.py`, `agent/session_lease.py`, `agent/model.py` |
| Omp harness | `agent/harness.py` (482) — events, steering, pause, tool-result marking, speculative execution |
| Agent extras | `agent/delegate.py`, `agent/curator.py`, `agent/modes.py`, `agent/extensions.py`, `agent/magic_keywords.py` (420), `agent/security.py` |
| Tools | `tools/registry.py` (219) + 30 families: coding, file_ops (370), search, terminal, todo, clarify, edit_pipeline, execute, lsp, dap, ide, delegate, approvals, mcp_client, mcp_session, plugins, browser, browser_egress (1771), playwright_browser, devices, x (349), telegram (260), discord (240), lead (1292), systems (489), webpack (570), mobile (936), infra (484), quality (652), packs (485), growth, offer, platform, rpc, exec_jobs, ultrathink (225), substrate_tools (333) |
| Providers | `providers/` — base (243), http (350), destination (2105), openai (461), anthropic (276), gemini (262), xai |
| Growth | `skills_runtime/manager.py` (282), `memory/store.py` (221), `memory/hindsight_service.py` (252), `learning/{autolearn,advisor,goals}.py`, `agent/curator.py`, `session/{persist,search}.py` |
| Durability | `durable/journal.py` (SQLite turn journal), `durable/workflows.py` (checkpointed workflows), `cron/` (scheduler + APScheduler backend) |
| Surfaces | `mcp_server.py` (448), `substrate/client.py` (333), `greptile/kb_sync.py` (352), `evals/` (runner 276, pyrit_target 231), `hosting/{openshell,agentos}/`, `grokbot/{templates,rosters}` |
| Contracts | `contracts/tool-rosters/omega-prime.yaml` (versioned roster), `ownership.yaml`, `prompts/` + `assemble.py` + `prompts-assembled/` |
| Tests | `tests/` — 54 test files, 372 tests; `evals/cases/` — 26 cases |

## 2. Loop anatomy and extension points

`agent/conversation_loop.py::run_conversation(agent, user_message, system_message=None, conversation_history=None, task_id=None) -> dict` (v1 Phase 2, v2/v9 hardened):

1. Interrupt check (`agent/interrupt.py`) — stops before another model call
2. Iteration budget check (`agent/budget.py`; per-turn budget refills each turn)
3. Prompt built once, byte-stable across tool rounds (`prompt_builder.py`; LOOP-02)
4. Model call via provider (`providers/`, retry/usage/Responses/streaming since v9)
5. `turn_tool_round.run_tool_round` — assistant tool-call message + one tool
   message per call; a pending steer becomes its own user row after the tool
   row (LOOP-03)
6. or `turn_final_response.finish_text_response`
7. `turn_finalizer` — finalize; compression (`agent/compression.py`) is the
   only rewriter of prior context (LOOP-04)

**Extension points a Prime capability family can hook:**
- *New rostered tools* — the standard path (registry + roster; §3). RLM
  spawn/collect, harness CRUD, refine, goal, heartbeat, agent messaging all
  enter this way.
- *Turn events / beforeModelCall* — `agent/harness.py` event sink and hook
  (Omp port): autonomous-mode driver and goal continuation consult here.
- *Turn finalizer* — where autonomous continuation and compaction arms
  attach (Prime's `TurnBoundary` equivalent).
- *Modes* — `agent/modes.py` tool-map wrapper pattern (plan mode) is the
  precedent for gating capability families on/off.
- *Curator* — `agent/curator.py` post-turn hook is where /refine review
  attaches.

## 3. Tool-family integration recipe (v4/v5 precedent)

A new rostered tool family touches exactly:

1. `omega_prime/tools/<family>.py` — `register_<family>_tools(registry, ...)`
   + `<FAMILY>_TOOL_NAMES` list; handlers return JSON-safe dicts; errors are
   `{"error": "code: reason"}`; writes carry `requires_approval=True`.
2. `omega_prime/contracts/tool-rosters/omega-prime.yaml` — append the names
   in registration order and extend the header comment ("then <Family> names
   from `register_<family>_tools`").
3. Registration wiring where the agent's registry is built (coding → growth
   → delegate → platform → ide → x → telegram → discord → lead → systems →
   web → mobile → infra → quality → packs → ultrathink → substrate order).
4. Tests: `omega_prime/tests/test_<family>.py` with fake peers (hermetic,
   no network) + the roster drift-guard test (registered names == roster
   names exactly) + policy/composition tests when policy-visible.
5. Eval cases in `omega_prime/evals/cases/<family>.json` when the family
   changes refusal/approval behavior.
6. `assemble-prompts.sh --check` must stay green (template lists only what
   exists).

## 4. Existing equivalents and gaps

| Prime capability | Closest existing Omega module | What exists today | Gap the port fills |
|---|---|---|---|
| RLM spawn/collect | `agent/delegate.py` + `tools/delegate.py` | One isolated child per goal; `background=True` handle; `join_delegate`; parent sees final response only | N named concurrent children, handle/selector collect with timeout snapshot semantics, list/delete with status vocabulary, progress notes, durable child sessions |
| Persistent REPL | `tools/execute.py` (`execute_code`) | Code execution tool | Session-persistent namespace, top-level await, snapshot size guards |
| Continual harness + /refine | `agent/curator.py` + `learning/autolearn.py` | Curator writes a skill when a turn earns one; autolearn captures after substantive turns | Four-scope harness state (prompt/memory/skill/subagent + factory), global scope, evidence-required refinement events, snapshots + rollback, reviewable diffs |
| Goals | `learning/goals.py` | Omp goals: objective + steps | Token budget accounting, turn-boundary continuation, stale-active detection, completion report |
| Heartbeats/schedules | `cron/` (scheduler, JobStore, APScheduler backend) | Cron re-enters the same agent on schedule | Session-targeted heartbeat job kind + scheduled-jobs artifact scan |
| Autonomous mode | `agent/budget.py` (iteration budget) | Per-turn iteration budget | Multi-dimensional budgets (turn/token/time), shell quality gates with retry windows, continuation policy at turn boundaries |
| Agent messaging | — (none) | — | Net-new: session registry + send/observe tools, family view (parent/children/siblings) |
| Compaction arms | `agent/compression.py` | Compression as the only context rewrite | Arm taxonomy (overflow retry / model-requested / threshold) as named paths |
| Executable skills | `skills_runtime/manager.py` + skill tools | Markdown skills with frontmatter guards | Importable Python-package skills |
| Session persistence/archiving | `durable/journal.py` + `session/persist.py` | SQLite turn journal, crash resume, session search | Append-only JSONL session layout + archive-by-age/count maintenance routine |
| Prompt layering + harness digest | `assemble.py` + `prompts/` | Deterministic byte-stable layered assembly | `[harness-digest]` as a separate user message; layer-breakdown dump |

## 5. Config system today (and where Prime flags live)

There is **no central settings module**. Configuration today is:
- Per-subsystem JSON documents loaded from explicit paths — e.g.
  `policy/policy.py:35 SeatPolicy.load(path)` (`json.loads(target.read_text())`,
  line 41); durable journal/workflows paths passed by callers.
- Environment variables at provider edges (xAI/Anthropic/OpenAI keys).
- Grok Bot template + setup flow (`grokbot/templates/`, `setup_check.py`)
  for deployment-time choices.

**v10 implication (LOOP-05):** introduce one small config surface —
`omega_prime/config.py` reading an optional JSON file (stdlib-only, the
`SeatPolicy.load` precedent) plus `OMEGA_PRIME_*` env overrides — carrying
`prime.<family>.enabled` flags, all default-off. Every Prime tool family
registration reads its flag; disabled ⇒ not registered, absent from roster
and prompt (drift-guard tests learn the gated shape).

## 6. Durability story today

- `durable/journal.py`: SQLite turn journal — durable runs resume after a
  crash (v2).
- `durable/workflows.py`: checkpointed workflows.
- `session/persist.py` + `session/search.py`: message persistence (sqlite)
  and search.
- `cron/`: JSON store authoritative; scheduler entries memory-only; fires
  serialized (v4 decision).
- Runtime artifacts are gitignored (`omega_prime/sessions.db`).

Prime's append-only JSONL session layout + archive policy lands as an
additive `session/` format, not a replacement for the journal.

## 7. Packaging / CI

- `pyproject.toml` (hatchling-style metadata, pytest/ruff/mypy config),
  `requirements-lock.txt` committed (v9 HYG-04), Python floor 3.11, CI
  matrix 3.12–3.14.
- `.github/workflows/`: CI runs suite + evals + assemble check + ruff +
  mypy + catalog check (v8/v9). A Rust parity-oracle job (Phase 54) slots
  in as a new workflow file scoped to `prime-agent/` paths, so Python-only
  changes don't pay Rust build time.
- No Rust toolchain in the Python dev loop; the parity oracle is CI +
  manual (`cargo test --workspace --locked`).

## 8. Unknowns

1. Exact registration call-site for tool families (which module builds the
   production registry) — read at Phase 55 start (`tools/registry.py`
   consumers; likely `agent/conversation_loop.py` or an agent factory).
2. Whether `learning/goals.py` has a persistence home today or is
   turn-scoped — read before extending it (Phase 57).
3. Eval-case JSON schema for tool-stubbing (v5 precedent: pack evals stub
   tools) — read `evals/runner.py` when adding Prime eval cases.
