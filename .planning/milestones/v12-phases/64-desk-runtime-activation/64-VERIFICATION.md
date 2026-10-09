# Phase 64 Verification

**Date:** 2026-10-09. **Tree:** branch `v12-programming-desk-merge`.

| Gate | Result |
|---|---|
| `ruff check omega_prime/` | exit 0 |
| `ruff format --check omega_prime/` | exit 0, 343 files formatted |
| `python -m mypy omega_prime/` | exit 0, 308 source files |
| `python -m pytest omega_prime/tests -q` | exit 0, 1916 passed, 12 warnings |
| `python -m omega_prime.evals.runner omega_prime/evals/cases` | exit 0, 26 passed |
| `bash omega_prime/scripts/assemble-prompts.sh --check` | exit 0 |
| `python -m omega_prime.tooling.catalog --check` | exit 0 |
| `python -m omega_prime.setup_check --root .` | exit 0, registry serves 109 roster tools |

## Requirement evidence

- **DESK-01.** `omega_prime/tests/test_desk_wiring.py::test_lead_doctor_green_on_memory_tools_substrate_without_credentials` and `test_shared_memory_store_identity` and `test_desk_stores_live_under_state_dir`. Doctor checks memory/tools/substrate are green with an empty env. Growth `memory` retain is visible to `lead_memory_recall`. Intake/packs/events files land under `OMEGA_PRIME_STATE_DIR`.
- **DESK-02.** `test_work_root_jails_coding_tools_and_keeps_install_lookups`, `test_default_coding_jail_is_unchanged`, `test_load_runtime_work_root_contract`, `test_help_advertises_work_root`. A foreign tree is editable and searchable; a path outside it is refused; ownership still resolves from the install root; the default jail stays `root/omega_prime`.
- **DESK-03.** `test_delegate_without_provider_env_is_not_configured`, `test_delegate_parent_with_provider_env`, `test_delegate_parent_shim_runs_a_scripted_child`. `setup_check` reports 109 roster tools. No provider env returns `{"error": "not_configured: provider"}`.
- **DESK-04.** `omega_prime/tests/test_desk_lead.py` end-to-end intake → claim → dispatch → `validate_receipt` → ack, plus the no-parent blocked receipt (never "no dispatcher" from the scheduler). `test_desk_driver_runs_due_passes_without_manual_calls` shows `DeskDriver` claims and acks a due pass. `SchedulerService` passes `skip_kind=desk_lead_pass`.
- **DESK-08.** Bus, docs index, and notify URL are read in `default_registry` and stored on `LeadContext` only when set. Unset paths keep the existing `not_configured` results (covered by the lead suite, still green).

## Fixes during verification

- Two new tests failed on first run: the scheduler test read a stale in-memory intake snapshot (the pass had written `done` to the shared file), and `lead_doctor` returned `approval required` because the tool is gated. Both were test-construction bugs; the assertions were not weakened.
- `register_growth_tools(memory=...)` shadowed the inner memory handler (mypy). The parameter is `memory_store`.
- `default_registry` must not start `DeskDriver`. Doctor, setup check, and unit tests all build a registry; a ticking thread there writes `cron/jobs.json` as a side effect. The live server starts and stops the driver.
- Desk wiring tests pass `OMEGA_PRIME_STATE_DIR` so they do not write `omega_prime/memory/MEMORY.md` or `omega_prime/state/` into the source tree.

## Not in this phase

DESK-05 (gates against an arbitrary repo), DESK-06 (receipts checked against captured commands, operator approver), DESK-07 (Railway, Greptile, Vercel, Playwright, Play, App Store clients) are Phase 65. Docs that still say "108 tools" or "delegate_task is not served" are Phase 66.
