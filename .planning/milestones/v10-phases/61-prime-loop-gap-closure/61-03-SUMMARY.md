---
phase: 61-prime-loop-gap-closure
plan: "03"
subsystem: prime-connectors
tags: [typed-boundary, versioning, approval, consumer-recovery]
status: product_verified_review_repaired
requires:
  - phase: 58
    provides: Existing typed versioned request/view connector convention
provides:
  - All five existing registered Prime families consume strict typed requests and views
  - Policy and approval still precede decoding and capability side effects
  - Actual consuming-loop raises, timeouts, malformed requests/responses and recovery evidence
affects: [61-04, 61-05, 61-06, v10-closeout]
tech-stack:
  added: []
  patterns: [existing connector cutover, authorization before decode, typed error propagation]
key-files:
  modified:
    - omega_prime/prime/types.py
    - omega_prime/prime/errors.py
    - omega_prime/prime/rlm.py
    - omega_prime/prime/harness.py
    - omega_prime/prime/goals.py
    - omega_prime/prime/autonomous.py
    - omega_prime/prime/messaging.py
    - omega_prime/tools/rlm.py
    - omega_prime/tools/harness.py
    - omega_prime/tools/goals.py
    - omega_prime/tools/autonomous.py
    - omega_prime/tools/agent_message.py
    - omega_prime/tools/registry.py
    - omega_prime/tests/test_prime_contracts.py
    - omega_prime/tests/test_prime_failure_injection.py
key-decisions:
  - "Reuse the existing typed connector boundary; no second adapter convention or compatibility shim."
  - "Accept explicit versions/extra fields at handlers so the strict decoder diagnoses them after authorization."
  - "Registered errors retain error/code/reason; the existing loop error string preserves code/reason without swallowing provider/control-flow failures."
requirements-completed: [CONN-01, CONN-03]
coverage:
  - id: registered-strict-consumer
    description: Actual authorization, strict type/version/unknown-field errors, worker failure, bounded timeout and valid recovery
    requirement: CONN-01
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_typed_loop_smoke
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_prime_contracts.py
        status: pass
    human_judgment: false
  - id: malformed-producer-recovery
    description: Actual stored malformed goal response reaches model-visible error and valid clear/set recovery
    requirement: CONN-03
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_actual_malformed_response_smoke
        status: pass
      - kind: regression
        ref: omega_prime/tests/test_prime_failure_injection.py
        status: pass
    human_judgment: false
completed: 2026-10-09
---

# Plan 61-03 — Registered typed consumers

`TypedConsumerRepair` executed the bounded source slice. Parent rejected its initial
helper-only/incomplete consumer evidence, required the real consuming paths, then
integrated and verified the returned continuation. No worker ran mid-flight checks
or committed. The first independent deep review of this slice found two blockers and
fourteen warnings (preserved in `61-REVIEW-pre-repair.md`); the review-repair wave
recorded below cleared them and the post-repair review (`61-REVIEW.md`) is clean. This
summary is not a full32 or signed A09 gate.

## Delivered behavior

RLM lifecycle/list, goal lifecycle/status and autonomous lifecycle/status use the
existing request/view pattern alongside the earlier operations. Every registered
handler of the seven Prime families (RLM, harness, goals, heartbeat, autonomous,
messaging, kernel) accepts only its declared parameters plus an explicit
`schema_version`; any other key is `unknown_field` and is never merged into a decoded
payload, omitted required fields are `bad_type`, versions below 1 or above the
adapter's are typed errors. Heartbeat and the eleven kernel tools decode through the
new `prime/heartbeat.py` and `prime/kernel.py` adapters. A denied malformed call never
gets as far as host creation. No approval flag, policy permission or native engine was
introduced by this cutover. The existing live goal/driver bindings remain the
loop's authoritative resources.

## Actual verification

The standalone registered RLM/actual Omega loop smoke completes12 model calls,
zero remaining: denial before effects; authorized boolean type, future-version
and unknown-field errors; worker raise; event-blocked running timeout; actual
child Omega/scripted-model prompt privacy; durable collect and valid recovery.
A separate actual Omega goal loop consumes a malformed persisted status, reports
the typed error, clears it and creates valid active state in four model calls.
Both exit0. These are not guarded-hook-only, forwarding/mock echoes, or fake
producer success. Exact inputs/outputs are retained in `61-EVIDENCE.json`.

Integrated full suite:739 passed/12warnings. Fresh actual-source snapshot install:
726 passed/13skipped/12warnings, followed by setup0. Later type-only fixture and
narrowing corrections are included in the fresh suite. Final Ruff0,271 formatted
files, mypy236 sources0,26 evals0 and actionlint0 are retained separately.

## Parent corrections and limitations

Parent retired a JSONL suffix pin instead of repinning JSON and changed recovery
assertions to consume actual structural model tool payloads, not `json.dumps`
substring escaping. Timeout regressions release/shut down their event-blocked
workers deterministically. Cold registry import of the optional Prime error type
now occurs inside dispatch; typed hook views load at the actual capability
boundary (Plan06), preserving legacy exports and avoiding the observed cycle.

CONN technical evidence does not waive literal LOOP-07's376pass/two frozen old
incidental-pin failures, Cargo packaging or DONE lifecycle gates. Current
requirements/audit must follow the independent full32 report before closeout.

## Review-repair wave (2026-10-09)

The first independent deep review (2 critical, 14 warning, 5 info) and the full32
integration audit's BUG-1 were repaired through ten file-disjoint units plus docs, then
re-reviewed independently (0 open findings; one new warning, WR-15 blank
objective/name, was found and fixed inside that pass).

- **Blockers:** model-supplied `sender`/`session` can no longer override the bound
  messaging identity (CR-01); an unparseable or non-object tool-call argument payload is
  an `error:` row and the tool is never called (CR-02).
- **Typed boundary:** declared-only tool surface, bad_type for omitted required
  fields, registry-owned error conversion with `error` audit verdicts, `scope` and
  `stale_after_turns` aliases rejected, atomic replace-all `goal_set`, finite
  `max_minutes`, typed heartbeat and kernel adapters (WR-01..05, BUG-1).
- **RLM:** explicit parent contract (`session_dir`, `session_name`, `delegate_depth`,
  `max_depth`, `max_children`; `require_parent`), no cwd default, `rlm_create_session`
  without `cwd`, roster record after admission, recovery that rewrites only interrupted
  records and survives a write failure, prompt/answer-free tombstones, settled-only
  answer/error, two-lock registry with atomic admission (WR-06..11).
- **Loop and tooling:** refusal stop reasons scoped to the most recent tool round
  (WR-12); `assemble-prompts --enable-family` requires `--output` and never touches the
  canonical artifact (WR-13).
- **Evidence (`61-EVIDENCE.json#review_repair_wave`):** a probe of 17 reviewed defects
  reproduces all 17 on a pre-repair source snapshot and none on the repaired tree;
  208 new tests in seven new files (170 fail or error on the snapshot, 38 are ordering
  or regression guards that already passed) plus the named new tests in four existing
  files all pass; full suite 980 passed, Ruff, format, mypy 245 sources, 26 evals,
  assembled-prompt and catalog checks, setup check all exit 0; Prime tools served
  through the real stdio MCP server (typed failures flagged `is_error`, valid writes
  persisted across server processes); the independent full32 integration re-check
  (`61-INTEGRATION.md`) mechanically proved all 37 registered Prime tools reject
  undeclared keys and bad versions with typed envelopes (27 WIRED / 3 BROKEN /
  2 HUMAN_NEEDED); a fresh venv install of the working tree (before the last 18
  round-trip tests) with the pinned public Prime checkout ran 949 passed / 13 skipped
  and setup 0.
- **Not changed on purpose:** IN-01/02/04 and the `rlm_collect` timeout/interrupt bound
  (IN-03 remainder) keep their documented contracts; the pre-v10 transcript comparator
  keeps its test-local dispatcher so the historical oracle stays byte-identical.
- **Still open (user decisions, not repaired here):** the literal unmodified historical
  suite is 376 passed / 2 incidental-pin failures before and after this wave (LOOP-07);
  Cargo source-only resolution exits 101 (REPO-04); milestone completion, archive,
  cleanup and publication need explicit authorization (DONE-01/02).
