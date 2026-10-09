# Phase 64 Plan: Desk runtime activation

**Goal**: The desk runtime is real: lead tools return live results, the agent can program a
target repo, `delegate_task` is served, and the lead pass claims intake and dispatches
tickets in production. Requirements: DESK-01, DESK-02, DESK-03, DESK-04, DESK-08.

**Evidence base**: `64-CONTEXT.md` (SEED-005 8/8 CONFIRMED-GAP with `path:line` citations).

## Design

1. **Desk context wiring (DESK-01).** In `omega_prime/mcp_server.py` `default_registry`
   (~lines 176-238): construct one shared `MemoryStore` (reuse the `memory_dir` resolution
   already used for growth tools, `mcp_server.py:179-183`), `IntakeStore`, `RosterStore`,
   `EventStore` under `OMEGA_PRIME_STATE_DIR`, pass them plus the existing `SubstrateClient`
   and the `ToolRegistry` into `LeadContext` (`mcp_server.py:206`; fields at
   `omega_prime/tools/lead.py:289-304`). `lead_doctor` (`lead.py:717-731`) then reports green
   on memory/tools/substrate with no credentials. `docs_index`/`notify`/`bus` stay optional
   and degrade loudly (DESK-08): `lead_docs_search` keeps its `not_configured` result with the
   reason surfaced in the Grok Bot template; no silent `{ok: true}` degradation
   (`lead.py:637-639` event_emit gets a real substrate-backed emission).
2. **Install root vs work root (DESK-02).** `main`/`load_runtime` gain `--work-root` and
   `OMEGA_PRIME_WORK_ROOT` (default: root). The work root flows to
   `register_coding_tools(registry, work_root / …)` — the current `root / "omega_prime"`
   default becomes "work root's `omega_prime` only when work root == install root" — to the
   IDE/LSP/DAP jail (`omega_prime/tools/ide.py:31-33,52-57,82-86`), `FileWorkspace`
   (`file_ops.py:39-42`) and `QualityContext.root` (`mcp_server.py:217`). Roster/policy/
   contract/prompt/ownership lookups stay on the install root (`mcp_server.py:521-535`).
3. **Delegate served (DESK-03).** `default_registry` builds a parent handle (session id when
   hosted, in-process agent shim otherwise — the same provider/env wiring the loop uses) and
   calls `register_delegate_tools(registry, parent)` (`omega_prime/tools/delegate.py:18`).
   Update the witnesses of the old omission: `omega_prime/setup_check.py:80-103`,
   `omega_prime/tests/test_mcp_server.py:130-141`, `omega_prime/grokbot/doctor.py:43-53`,
   `omega_prime/tooling/catalog.py:92,107`. Served count becomes 109; manifest, `/healthz`,
   `catalog --check` and the roster must agree.
4. **Lead pass live (DESK-04).** A production dispatch closure
   (ticket → delegate/RLM subagent → receipt dict per `omega_prime/receipts.py` shape) is
   wired into `run_lead_pass` (`omega_prime/routines/desk_lead.py:20-113`), invoked from the
   cron scheduler as a job kind (or heartbeat tick) sharing the same `IntakeStore` as the
   lead tools. No `dispatch=None` in production.
5. **Desk env surface (DESK-08).** `OMEGA_PRIME_DESK_BUS_URL`, `OMEGA_PRIME_DESK_NOTIFY_*`,
   `OMEGA_PRIME_DESK_DOCS_INDEX`, `OMEGA_PRIME_WORK_ROOT` follow the existing env wiring
   pattern (`mcp_server.py:127-135,193-238`); unconfigured optionals produce explicit
   `not_configured: <reason>` results.

**Integration contract** (shared `mcp_server.py`): ONE task owns `omega_prime/mcp_server.py`
end to end (items 1-3, 5) and exposes `runtime.parent` + `work_root` on the runtime object;
the lead-pass task codes against that contract (`dispatch` closure imports the parent factory)
and touches `omega_prime/routines/desk_lead.py`, `omega_prime/cron/`, tests only.

## Verification loops (every loop must be real, SEED-014)

- V1 `lead_doctor` green on a real launched host process (subprocess + socket), not only
  in-process.
- V2 A test edits a file in a synthetic foreign repo under the work root via
  `edit_file`/`search_text`/`lsp_diagnostics`; an escape attempt is refused.
- V3 MCP client over a real socket lists `delegate_task` and calls it; the child returns.
- V4 An intake record flows claim → ticket → dispatch → receipt → ack on real JSON stores.
- V5 Full gates: `pytest omega_prime/tests`, evals runner, `assemble-prompts.sh --check`,
  `catalog --check`, `setup_check`, `ruff check`, `ruff format --check`, `mypy omega_prime/`,
  pyright on changed files.

## Tasks

- **64-A (integration owner)**: `omega_prime/mcp_server.py`, `omega_prime/tools/lead.py`
  (constructor/docstring touches only), `omega_prime/tools/ide.py` (jail parameter),
  `omega_prime/setup_check.py`, `omega_prime/tooling/catalog.py`,
  `omega_prime/grokbot/doctor.py`, `omega_prime/tests/test_mcp_server.py`,
  `omega_prime/tests/test_desk_wiring.py` (new). Items 1-3, 5.
- **64-B (lead pass)**: `omega_prime/routines/desk_lead.py` (dispatch closure),
  `omega_prime/cron/scheduler.py` (job kind/entry), `omega_prime/tests/test_desk_lead.py`
  E2E. Item 4. Depends on 64-A's contract only (names, not its diff).

## Risks

- `delegate_task` on the host needs a provider (model) for child turns: reuse the loop's
  provider factory; if no provider env is set the tool returns an explicit
  `not_configured: provider` result (honest, DESK-08 style) rather than a fake child.
- Registry serving count changes (108 → 109) touch docs counts and `61-05` fixture
  expectations: update fixtures with the code, never weaken assertions.
- The cron scheduler runs model-driven jobs; the desk pass must serialize with foreground
  turns (v10 heartbeat precedent, `61-02`).
