# Phase 56 — Continual harness port — SUMMARY

## What was done

Ported Prime Agent's continual-harness capability family into Omega Prime as
pure Python (behavior port, per the v10 architecture decision: no PyO3/maturin
bridge — Prime's Rust↔Python wiring is a spawned-kernel process boundary, and
Omega Prime's rule is one Python process).

Source contract: `prime-agent-runtime/src/rlm/harness.py` +
`pa-core/src/refinement/` @ `967eb13f` (MIT, PrimeIntellect — see VENDOR.md).

New modules:

- `omega_prime/learning/harness.py` — `HarnessState`, the supplemental-state
  store. Five kinds (`prompt`, `memory`, `skill`, `subagent`, `factory`),
  session-local scope by default with an opt-in cross-session `global` scope,
  strict per-kind entry-shape validation, and refinement events that require
  trigger + changes + **evidence** + outcome (the "evidence-backed updates
  only" rule — evidence is mandatory). Every applied refinement snapshots the
  prior state; `rollback()` restores the exact prior bytes. `save()` refuses
  to clobber a file whose mtime changed since load (the port of Prime's
  `_sync_from_disk` intent for a single-process host — no lock-dir needed).
- `omega_prime/agent/refine.py` — the deterministic `refine()` pass. Reviews
  proposals against the current trajectory and applies only those whose every
  evidence string appears in the trajectory text. Never rewrites the immutable
  base system prompt (HARN-04). Returns a reviewable diff (applied entries,
  rejected proposals with reasons, recorded refinement event). A refinement
  with no evidence applies nothing and records nothing.
- `omega_prime/tools/harness.py` — the `harness_*` tool family
  (`HARNESS_TOOL_NAMES` = harness_upsert, harness_get, harness_list,
  harness_delete, harness_refine, harness_rollback). Writes require approval;
  reads do not. `register_harness_tools(registry, root, *, enabled=True)` is
  gated on the `prime.harness.enabled` config flag (default off).

Wiring (the tool-family recipe):

- `contracts/tool-rosters/omega-prime.yaml` — appended the six harness names
  after the RLM names; header comment updated.
- `contracts/policies/omega-prime.json` — added the six names to the allowlist.
- `tooling/catalog.py` — added `("Harness", HARNESS_TOOL_NAMES)` to FAMILIES;
  regenerated `docs/tool-catalog.md`.
- `mcp_server.py` `default_registry` — registers the harness family when
  `prime.harness.enabled` is set. Unlike RLM (which needs a live parent agent
  and is skipped here), the harness family is self-contained (needs only
  `root`), so it registers in the default registry when enabled.
- `setup_check.py` — harness added to the gated set (config-gated, default
  off, so absent from the default registry unless the flag is on).
- Drift-guard tests updated: `test_tools.py`, `test_growth.py`,
  `test_providers.py` (roster concatenation + registration),
  `test_mcp_server.py` (gated set).

## Deviations from the plan

- The `HarnessState.list()` method was renamed to `list_entries()` during
  implementation: the name `list` shadowed the builtin within the class body
  and broke subsequent `list[...]` annotations under mypy. Internal API with
  no external consumers; renamed for correctness.
- The mtime-clobber test forces a distinct mtime via `os.utime` because
  `save()` re-stats after write, so a same-second concurrent write would not
  be caught by wall-clock mtime alone.

## Validation evidence

- `pytest omega_prime/tests/test_continual_harness.py` — 19 passed (state CRUD,
  all five kinds, validation, local/global separation, mtime clobber refusal,
  refinement evidence requirement, snapshot/rollback, refine pass
  apply/reject/no-op, tool registration, approval gating, dispatch roundtrip).
- `pytest omega_prime/tests` (full suite) — 439 passed (was 420 pre-Phase 56;
  +19 harness).
- `python -m omega_prime.evals.runner omega_prime/evals/cases` — 26 passed, 0 failed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` — up to date.
- `python -m omega_prime.tooling.catalog --check` — up to date.
- `python -m omega_prime.setup_check --root .` — registry serves 108 roster tools.
- `ruff check omega_prime/` — all checks passed.
- `mypy` on the new/changed modules — no issues.

## Acceptance criteria

- Harness state store with five kinds, two scopes, strict validation,
  evidence-backed refinement, snapshot + exact rollback — met.
- Deterministic refine pass, evidence-gated, base prompt never rewritten — met.
- Tool family registered + rostered + cataloged, writes approval-gated — met.
- Config-gated (default off); flags-off behavior matches pre-v10 — met
  (default registry unchanged unless `prime.harness.enabled`).
