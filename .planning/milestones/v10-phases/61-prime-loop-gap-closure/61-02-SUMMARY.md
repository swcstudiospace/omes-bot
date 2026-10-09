---
phase: 61-prime-loop-gap-closure
plan: "02"
subsystem: scheduler
tags: [prime, heartbeat, apscheduler, session-lease, shutdown]
requires:
  - phase: 57
    provides: Persisted heartbeat schema and cron machinery
  - phase: 61-01
    provides: Generic registry bindings and named live-agent composition
provides:
  - Registry-bound production scheduling re-enters named live sessions
  - Opt-in lease waiting without holding bookkeeping locks across callbacks
  - Fresh-state claim/finish reconciliation and retryable, ownership-safe shutdown
affects: [v10-closeout]
tech-stack:
  added: []
  patterns: [per-binding runner and sink snapshots, claim-run-fresh-finish, lifecycle epochs, drain-before-return]
key-files:
  modified:
    - omega_prime/agent/session_lease.py
    - omega_prime/cron/heartbeat_runtime.py
    - omega_prime/tools/heartbeat.py
    - omega_prime/tests/test_heartbeat_runtime.py
    - omega_prime/cron/heartbeat.py
key-decisions:
  - "Foreground acquisition remains fail-fast; heartbeat runs explicitly wait for the same lease."
  - "Callbacks and diagnostic sinks execute outside the bookkeeping lock."
  - "Conditional detach and stop-if-empty are one ownership decision; shutdown failures remain observable and retryable."
  - "A later explicit stop cancels stale last-owner restart; start during drain raises instead of returning fake success."
  - "Use list_jobs for the new runtime listing API and migrate every caller; no list alias remains."
requirements-completed: [LOOP-02, LOOP-06]
coverage:
  - id: named-live-scheduling
    description: Real scheduler delivers persisted beats to the correct live named session without overlapping foreground work
    requirement: LOOP-02
    verification:
      - kind: integration
        ref: omega_prime/tests/test_heartbeat_runtime.py
        status: pass
      - kind: integration
        ref: .venv/bin/python /root/.hermes/cache/scratch/phase61-native-scheduler-proof-01a11a5f.py
        status: pass
    human_judgment: false
  - id: scheduler-degradation
    description: Failed or unserializable beat outcomes are recorded and redacted for the owning session without killing scheduling
    requirement: LOOP-06
    verification:
      - kind: integration
        ref: omega_prime/tests/test_heartbeat_runtime.py
        status: pass
      - kind: integration
        ref: .venv/bin/python /root/.hermes/cache/scratch/phase61-native-scheduler-proof-01a11a5f.py
        status: pass
    human_judgment: false
completed: 2026-10-08
status: complete
---

# Phase 61 Plan 02 — Named-session production heartbeat scheduling

**Persisted heartbeat jobs now drive the owning live conversation through APScheduler, with lease serialization, fresh reconciliation and settled shutdown.**

## Accomplishments

- `HeartbeatRuntime` owns the existing jobs file and an optional owned scheduler; tools reuse the same registry-bound runtime for the same path. Tool names, JSON schemas and approval flags are unchanged. The new runtime's listing method is `list_jobs()`.
- Every claim checks heartbeat kind, due state and per-job in-flight ownership. The runtime captures the named runner/sink together, releases the bookkeeping lock for work, then finishes against fresh disk state. Clear during work cannot resurrect the row; concurrent updates are retained; foreign cron rows remain untouched.
- The existing lease now supports `acquire(wait=True)` atomically. Default foreground callers still fail fast. Reentrant schedule/list/clear and diagnostic sinks do not deadlock with waiting beats.
- Unknown sessions and malformed jobs produce explicit error outcomes, not fresh conversations. Ordinary callback/serialization failures persist redacted structured errors and route degradation to the owning binding; `BaseException` propagates and releases claims.
- Stop/close/last-owner detach drain both scheduler callbacks and overdue-start callbacks. Self-callback blocking shutdown is rejected before mutation. Failed cleanup can be retried, including after the binding was already removed.
- Owned scheduler pools are recreated on restart; injected schedulers are not silently replaced. A lifecycle epoch and latest-resume token prevent an older detach cleanup from restarting a later-stopped service. Starts during a drain raise; no silent `[]` success remains.
- Interval projection explicitly supplies the first next-run deadline, including due-now. Projection translates the injected clock's remaining delay onto the scheduler's wall clock rather than replaying decades of missed intervals.
- Invalid calendars are rejected before disk mutation, including intervals that cannot advance or round to APScheduler's implicit one-second fallback. Malformed persisted heartbeats diagnose once and remain disarmed; valid neighbors still deliver. Nonobject/foreign rows are preserved; whole-file corruption or an owned missing identity fails explicitly.
- Injected backend foreign entries remain untouched. A dead injected executor cannot restart silently: callers receive an explicit error and must supply a fresh backend. `misfire_grace_time=None` permits exactly one persisted overdue catch-up after a scheduler stall.

## Verification

The parent ran the affected 15-file pytest suite (234 passed in 7.42s, exit 0), full Python suite (686 passed in 30.66s after retiring three static source-pin tests, 12 dependency warnings, exit 0), Ruff check, formatter check (271 files), mypy (236 files), all 26 evals, prompt/catalog checks and setup (108 tools), all final exit 0. Actionlint and pip audit also exited 0. Exact outcomes and the corrected initial import-lint failure are in Plan 01 and `61-EVIDENCE.json`; no worker claims parent checks.

### Native scheduler receipts

Temporary `phase61-native-scheduler-proof-01a11a5f.py`, exit 0, used actual APScheduler, real loaded Rust HTTP provider, real approvals/disk tools and two named `OmegaPrimeAgent.from_prime` instances:

| Receipt | Observed result |
|---|---|
| Named live lease | Alpha's foreground tool held the lease; its due beat waited while Beta's beat completed independently. Alpha made 3 HTTP requests, Beta 4; distinct beat prompts reached the correct transcripts. |
| Reentrant tools and clear | Foreground list/clear completed while the beat waited. Cleared Alpha job/entry was not resurrected; Beta's actual callback response `"actual shared disk fact"` was persisted. Closing Alpha preserved Beta; last close settled scheduling. |
| Binding error isolation | Actual Alpha HTTP 400 produced a redacted heartbeat `prime_degraded` event only for Alpha. Beta had no degradation and retained its actual response. Explicit Alpha foreground recovery returned `native recovered`. |
| Paid provider-error accounting | A later HTTP 400 preserved `ProviderError`; preceding goal/driver usage was 12 tokens each, no gate ran, explicit retry succeeded without charging the stopped driver twice. |
| Thread settlement | After all agents and HTTP peers closed, Python thread enumeration contained only `MainThread`. |

The due-now native deliveries prove the interval-first-run fix. Separate pre-fix probes observed a stale last-owner cleanup restarting a later-stopped backend and a due-now beat waiting its interval. Corrected probes observed backend `STATE_STOPPED`, preserved replacement binding, explicit RuntimeError for start during drain, and immediate beat delivery. The permanent lifecycle regressions cover controlled interleavings; the timing-sensitive real due-now check was removed after recording smoke evidence, honoring this plan's no-wall-clock-test constraint.

The current bridge was also exercised after its header-only rebuild: pause the
actual scheduler for two seconds past a due beat, resume, observe two actual
native HTTP requests, one history entry and the persisted response
`actual resumed scheduler fact`; close settled Python threads. Separate real
HTTP probes proved malformed disarm, poison-row isolation and injected foreign
entry preservation with explicit dead-pool restart error. These timed probes are
throwaway verification, not permanent polling tests.

## Deviations and fixes

- Integration closed overdue-start drain, self-join/reentrant shutdown, cleanup-retry, stale conditional restart, owned-pool restart and immediate-first-beat defects. Real shutdown failures propagate rather than becoming clean success.
- `unbind(..., stop_if_empty=True)` was added to combine expected-runner detach and last-owner cleanup atomically; the Context and plan contract now record it.
- The new listing API was renamed from `list` to `list_jobs` after LSP identified all seven references; every tool/test caller migrated, with no compatibility alias. This avoids a class-namespace type collision without changing the user-facing `heartbeat_list` tool.
- Parent review expanded the shared heartbeat helper only for dict/identity-safe filtering. No store schema, generic JobStore, neighboring scheduler backend, native function/ABI or upstream-tree logic changed. Calendar validation, malformed disarm and owned-entry reconciliation are behavior fixes, not success fallbacks.
- Same-path registration checks now assert live set/list/clear behavior rather than catalog names, binding identity or forwarding echoes.
- Permanent source/default/wiring pins and fixed delays were removed. Calendar projection and overdue executor behavior are deterministic regressions using controlled clocks, events and a paused real backend; real wall-clock delivery remains separate smoke evidence.

## Threat Flags

No new unmitigated execution threat identified. Planned routing, argument, stale-entry, bounded-history, ownership and disclosure controls are supported by current regression/native receipts. Formal security closure belongs to the parent report; no newly accepted risk is asserted.

## Task Commits

No phase commit or publication yet. Executors made no commits or check runs; parent retains integration, documentation, lifecycle and shipping ownership with `commit_docs: false`.

## Limitations / Next Gate

No UI surface changed. Unconfigured external services are not claimed as tested. Unchanged upstream Rust/ext4 failures remain explicitly recorded, not rerun or called green. Phase verification, milestone audit and authorized archive/cleanup remain separate gates.
