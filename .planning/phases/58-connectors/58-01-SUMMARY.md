# Phase 58 — Connector layer + parity suite — SUMMARY

## What was done

Put every ported Prime capability behind a typed, versioned Python adapter —
the "connectors" of the merge (CONN-01) — and proved fidelity with contract
tests on both sides of each adapter (CONN-02), failure-injection tests
(CONN-03), and behavior-parity fixtures derived from the Rust/Python sources
(CONN-04).

New package `omega_prime/prime/`:

- `errors.py` — `PrimeError(code, reason)`; the wire shape is
  `"code: reason"`, matching the registry's `{"error": ...}` surface.
- `types.py` — the decode discipline (Prime's `_spawn_handle_from_payload`
  precedent): every field type-checked, booleans never pass as ints, unknown
  fields rejected, closed-vocabulary membership enforced, and a payload
  declaring a newer `schema_version` than the adapter's own rejected loudly
  (`unsupported_schema_version` — the pa-models forward-compat guard made
  loud, not silent).
- `rlm.py` — `RlmConnector` over `RlmHost`/`NoRlmHost` with `SpawnRequest`,
  `CollectRequest`, `ProgressNoteRequest`, `ChildResultView`; collect/list
  views enforce `COLLECT_STATUSES`/`SUBAGENT_STATUSES`/`ACTIVITY_KINDS`.
- `harness.py` — `HarnessConnector` over `HarnessState` with `UpsertRequest`
  and `EntryView`; kinds/scopes are the closed Prime vocabularies.
- `goals.py` — `GoalsConnector` over `PrimeGoalStore` with `SetGoalRequest`,
  `AccrueRequest`, `GoalStatusView` (closed status set + `cleared`).
- `autonomous.py` — `AutonomousConnector` building/driving
  `AutonomousDriver` with `StartRequest` (gate is an argv tuple, never a
  shell string) and `VerdictView` (stop reasons from the closed
  `STOP_REASONS` set).
- `messaging.py` — `MessagingConnector` over `SessionRegistry` with
  `SendRequest` and `MessageView` (verbatim Prime fields); unknown
  recipient/session raise `PrimeError("unknown_recipient"|"unknown_session")`
  — structured, never a silent drop.
- `__init__.py` — public surface; package `SCHEMA_VERSION` is the max of the
  per-adapter versions (all 1).

Tests:

- `tests/test_prime_contracts.py` (29) — round-trip + rejection per adapter;
  a parametrized future-schema-version guard across all eight request types;
  tool-surface dicts decode back into typed views losslessly.
- `tests/test_prime_failure_injection.py` (7) — raising capability (settled
  into the child result, and separately wrapped by `guarded_hook` into a
  `prime_degraded` event with the loop continuing), collect timeout returns
  snapshots without hanging, malformed payloads are typed errors not
  tracebacks, unknown status strings are rejected at the boundary, gate
  failure is a structured stop and a stopped driver stays stopped.
- `tests/parity/*.json` + `tests/test_prime_parity.py` (6) — six fixtures
  with per-fixture upstream source citations: no-host error strings
  (rlm_host.rs), progress-note cap + throttle (rlm/__init__.py), collect
  timeout snapshot semantics, `goal_token_delta_for_usage` arithmetic cases
  (goals.rs), harness entry/event validation rejections (harness.py), and
  the closed status vocabularies.

## Deviations from the plan

- `UpsertRequest.to_dict`/`StartRequest.to_dict` serialize tuple fields as
  JSON lists (not via `asdict`) so `from_dict(to_dict(x))` round-trips —
  caught by the contract tests.
- Harness event-validation parity cases call the ported
  `_validate_refinement_event` directly: `record_refinement`'s keyword-only
  signature makes a missing key a Python TypeError before validation runs;
  the fixture pins the validation rules, which live in the validator.

## Validation evidence

- `pytest omega_prime/tests/test_prime_contracts.py
  test_prime_failure_injection.py test_prime_parity.py` — 42 passed.
- `pytest omega_prime/tests` (full suite) — 526 passed (484 pre-Phase 58).
- `python -m omega_prime.evals.runner omega_prime/evals/cases` — 26 passed.
- `assemble-prompts.sh --check`, `tooling.catalog --check` — up to date.
- `python -m omega_prime.setup_check --root .` — registry serves 108 roster
  tools (connector layer adds no roster tools; it types the existing ones).
- `ruff check` + `ruff format --check` — clean. `mypy` — no issues in 215
  source files.

## Acceptance criteria

- Every Prime capability call behind a typed adapter with a versioned
  schema (CONN-01) — met.
- Contract tests validate request/response shapes on both sides (CONN-02) —
  met.
- Failure-injection: raise/timeout/malformed/unknown-status → structured
  error, loop continues, no hang (CONN-03) — met.
- Parity fixtures derived from the Rust/Python baseline pass (CONN-04) —
  met.
