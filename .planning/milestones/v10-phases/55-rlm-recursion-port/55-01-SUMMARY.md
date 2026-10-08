# Phase 55: RLM recursion port

Refs SPE-8009. Ports Prime's RLM (recursive language model) sub-agent host to
Omega Prime as a default-off capability family, per v10 decision D1
(behavior-port to Python) and D4 (degrade-with-warning).

## Source contracts (prime-agent @ 967eb13)

- `pa-agent/src/rlm_host.rs` — spawn/collect/list/delete/rename/progress-note
  semantics, degraded-host error strings, status sets.
- `prime-agent-runtime/src/rlm/` — kernel-side child lifecycle.

## Added

- `omega_prime/config.py` — `PRIME_FAMILIES`, `load_config(root)` layering
  defaults (all off) ← `omega-prime.json` ← `OMEGA_PRIME_PRIME_<FAMILY>_ENABLED`
  env; `prime_enabled()`, `family_config()`.
- `omega_prime/agent/rlm.py` — `RlmHost` (ThreadPoolExecutor children;
  spawn/collect/list/delete/rename/progress_note/create_session), `NoRlmHost`
  (verbatim degraded error strings), frozen dataclasses
  (`RLMSpawnHandle`, `RLMChildResult`, `RLMSubagent`, `RLMSubagentActivity`,
  `RLMProgressNoteResult`, `RLMCreateSessionHandle`), closed status sets
  (`SUBAGENT_STATUSES`, `COLLECT_STATUSES`, `ACTIVITY_KINDS`), UTF-16
  512-char progress-note cap with 10s throttle, collect timeout degrades to
  snapshots (never raises).
- `omega_prime/tools/rlm.py` — `RLM_TOOL_NAMES` (rlm_spawn, rlm_collect,
  rlm_list_subagents, rlm_delete_subagent, rlm_create_session,
  rlm_progress_note, rlm_rename) + `register_rlm_tools(registry, parent, *,
  enabled=True, run_child=None, session_store=None)`; writes require approval.
- Tests: `tests/test_rlm.py` (39), `tests/test_prime_config.py`.

## Wiring (tool-family recipe)

- Roster `contracts/tool-rosters/omega-prime.yaml`: RLM names after substrate.
- Policy `contracts/policies/omega-prime.json`: allowlist updated.
- `tooling/catalog.py`: `("RLM", RLM_TOOL_NAMES)` family; `docs/tool-catalog.md`
  regenerated.
- Drift guards updated: `test_tools.py`, `test_growth.py`, `test_providers.py`.
- `mcp_server.py` / `setup_check.py`: RLM excluded from default-registry
  serving (needs a live parent, like `delegate_task`).

## Gates

- pytest: 420 passed. Evals: 26 passed. assemble-prompts --check, catalog
  --check, setup_check, ruff check/format, mypy: all green.
- Flags-off behavior matches pre-v10 exactly (family not registered, absent
  from prompt).

## Deviations

None.
