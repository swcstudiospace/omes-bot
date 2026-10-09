---
phase: 61-prime-loop-gap-closure
plan: "01"
subsystem: agent-loop
tags: [prime, goals, autonomous, usage-accounting, degradation]
requires:
  - phase: 57
    provides: Goal, autonomous, messaging, configuration and degradation helpers
  - phase: 58
    provides: Typed goal/autonomous contracts and failure-injection conventions
provides:
  - Registered goal and autonomous state drives bounded production turn boundaries
  - Paid model work is accounted once even when continuation is forbidden
  - Hook failures remain redacted, observable and non-fatal without extending work
affects: [61-02, v10-closeout]
tech-stack:
  added: []
  patterns: [fresh goal factory, live driver holder, cumulative call cap, accounting before continuation permission]
key-files:
  modified:
    - omega_prime/tools/registry.py
    - omega_prime/tools/goals.py
    - omega_prime/tools/autonomous.py
    - omega_prime/agent/prime_hooks.py
    - omega_prime/agent/conversation_loop.py
    - omega_prime/agent/runtime.py
    - omega_prime/tests/test_prime_loop.py
key-decisions:
  - "Keep one transcript, journal, lease, outer model-call cap and caller budget across implicit continuation."
  - "Charge successful paid work before terminal/provider-error boundaries without running a completion gate."
  - "Fresh paused/completed/cleared/stale/exhausted goal state vetoes autonomous continuation."
  - "A failed hook invocation emits its own redacted event; startup failure veto is retained for that public run."
requirements-completed: [LOOP-01, LOOP-03, LOOP-04, LOOP-06]
requirements-open:
  LOOP-05: completed by plan 61-05 (effective prompt and roster), not by this slice
  LOOP-07: literal unmodified historical suite is 376 passed / 2 incidental-pin failures; fixture comparison delivered by plan 61-06
coverage:
  - id: goal-boundaries
    description: Fresh persisted goal state controls continuation, completion reports and token/stale boundaries
    requirement: LOOP-01
    verification:
      - kind: integration
        ref: omega_prime/tests/test_prime_loop.py
        status: pass
      - kind: integration
        ref: .venv/bin/python /root/.hermes/cache/scratch/phase61-native-controls-proof-01a11a5f.py
        status: pass
    human_judgment: false
  - id: autonomous-limits-and-gates
    description: Real driver enforces turn/token/time budgets and executes configured argv quality gates honestly
    requirement: LOOP-03
    verification:
      - kind: integration
        ref: omega_prime/tests/test_prime_loop.py
        status: pass
      - kind: integration
        ref: .venv/bin/python /root/.hermes/cache/scratch/phase61-native-controls-proof-01a11a5f.py
        status: pass
    human_judgment: false
  - id: hook-failure-containment
    description: Hook degradation is redacted and prevents implicit extension while preserving valid foreground response
    requirement: LOOP-06
    verification:
      - kind: integration
        ref: omega_prime/tests/test_prime_loop.py
        status: pass
      - kind: integration
        ref: .venv/bin/python /root/.hermes/cache/scratch/phase61-native-controls-proof-01a11a5f.py
        status: pass
    human_judgment: false
  - id: preserve-messaging
    description: Existing rostered cross-session messaging remains unchanged
    requirement: LOOP-04
    verification:
      - kind: integration
        ref: omega_prime/tests/test_agent_message.py
        status: pass
    human_judgment: false
  - id: preserve-default-off
    description: Disabled families retain existing roster, prompt and thread-free behavior
    requirement: LOOP-05
    verification:
      - kind: integration
        ref: omega_prime/tests/test_prime_config.py
        status: pass
      - kind: integration
        ref: omega_prime/tests/test_prime_loop.py
        status: pass
    human_judgment: false
  - id: preserve-loop
    description: Existing flags-off transcript and loop behavior remain intact
    requirement: LOOP-07
    verification:
      - kind: integration
        ref: omega_prime/tests/test_loop.py
        status: pass
    human_judgment: false
completed: 2026-10-08
status: complete
---

# Phase 61 Plan 01 — Goal/autonomous production turn boundaries

**Registered goal and autonomous controls now govern the existing bounded conversation loop, including once-only paid-work accounting and honest terminal stops.**

## Accomplishments

- The registry exposes an empty-by-default generic binding dictionary. Enabled goal registration publishes a fresh-store factory; autonomy publishes its actual live driver holder. Model tool requests still use `registry.dispatch` and its approval/policy enforcement.
- Goal reads are fresh at boundaries. External completion supplies the stored report; pause, clear, stale state and exhausted budgets stop continuation. Never-set goal absence does not veto independent autonomy.
- Public usage remains a lossless key-wise aggregate; goal/driver budgets derive and sum known totals per call, including mixed component-only/total-token shapes. Unknown usage remains unknown. Paid calls before provider failure and terminal cap/tail work are charged once, without running a completion gate.
- A stopped driver cannot restart from a cached reference. Real gates retain their producer diagnostics rather than losing stderr/detail fields during typed validation.
- Actual approval/policy error rows stop continuation; successful document content containing denial phrases is not treated as a refusal. Incomplete responses and outer-cap stops retain honest incomplete results.
- Runtime composition binds the owning named agent and redacted sink. Failed heartbeat startup retains the bound cleanup handle; close can detach it instead of leaking an owner.
- Normal Anthropic `end_turn` and `stop_sequence` completions reach continuation and real gates. Idle enabled families do not relabel an ordinary final-cap answer as failure. A later interrupted continuation retains the previously accepted answer.
- The inherited HARN-03 defect is repaired: refinement snapshots prior entries before writes, records only actually applied IDs even on a partial failure, and rollback restores prior entries exactly. Registered-tool regression also proves fixed base-prompt bytes through two actual agent turns (HARN-04).

## Verification

All commands ran from `/root/src/repos/omega-prime`; behavior checks used fresh HOME/XDG directories, the repository venv and scratch TMPDIR.

| Gate | Exit | Observed result |
|---|---:|---|
| Affected 15-file pytest suite listed in the phase evidence matrix | 0 | 234 passed in 7.42s |
| `.venv/bin/python -m pytest omega_prime/tests -q` | 0 | 686 passed in 30.66s after retiring three source-pin tests; 12 dependency deprecation warnings |
| `.venv/bin/ruff check omega_prime/` | 0 | All checks passed |
| `.venv/bin/ruff format --check omega_prime/` | 0 | 271 files formatted |
| `.venv/bin/python -m mypy omega_prime/` | 0 | 236 source files, no issues |
| `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` | 0 | 26 passed, 0 failed |
| `bash omega_prime/scripts/assemble-prompts.sh --check` | 0 | OMEGA_PRIME up to date |
| `.venv/bin/python -m omega_prime.tooling.catalog --check` | 0 | Tool catalog up to date |
| `.venv/bin/python -m omega_prime.setup_check --root .` | 0 | Roster/template/assembly valid; registry serves 108 tools |
| `actionlint .github/workflows/rust-parity.yml .github/workflows/supply-chain.yml` | 0 | CI syntax valid; no cloud CI execution claimed |
| `.venv/bin/python -m pip_audit --progress-spinner off -r requirements-lock.txt --ignore-vuln PYSEC-2026-4114` | 0 | No known vulnerabilities; one pre-existing documented exception |
| `cargo +1.98.1 build --locked --manifest-path native/omega-prime-prime/Cargo.toml --target-dir prime-agent/target` | 0 | Header-only bridge rebuild succeeded; inherited crossterm warnings unchanged |
| Installed `cargo-deny 0.20.2` against native manifest, `--locked --config deny.toml check licenses` | 0 | Native dependency graph: licenses ok |

The first final Ruff run caught an extra blank line left after deleting obsolete
documentation tests. LSP offered no import action; the owned blank line was
removed, then full Ruff and the affected formatter check returned exit 0.

Setup honestly skipped unconfigured Ultrathink/substrate bridges. These are not live external-service proofs.

### Native runtime receipts

The temporary `phase61-native-controls-proof-01a11a5f.py` ran with the real loaded Rust extension, localhost SSE HTTP peer, `OmegaPrimeAgent.from_prime`, real approved registry, actual disk-read tool and real argv gate processes. Exit 0; receipts were recorded before deleting the throwaway.

| Scenario | HTTP requests | Known tokens | Observed terminal result |
|---|---:|---:|---|
| Goal budget | 3 | 36 | `goal_budget_exhausted`; persisted goal tokens 36 |
| Autonomous turns | 3 | 36 | 2 turns, `autonomous_max_turns`, stopped |
| Autonomous tokens | 2 | 24 | 1 turn, `autonomous_max_tokens`, stopped |
| Autonomous time | 2 | 24 | 1 turn, `autonomous_max_minutes`, stopped |
| Gate pass | 2 | 24 | Actual marker file + exit 0; `autonomous_gate_passed` |
| Gate failure | 2 | 24 | Actual marker file + exit 7; `autonomous_gate_failed` |
| Approval refusal | 2 | 24 | `approval_refused`; denied handler performed no effect |
| Hook degradation | 2 | 24 | Valid text response retained; redacted goals events; no implicit retry |

Every scenario checked actual tool response bytes, aggregate usage, preserved native metadata/transcript prefix and the installed fixed system prompt plus caller suffix. Autonomous stops above report `completed: false`; they do not claim task success. In the degraded scenario the still-running driver was charged 1 turn/24 tokens but did not extend this public run.

The companion native scheduler proof also injected a real HTTP 400 after a successful 12-token tool round. The original `ProviderError` propagated; goal and driver each charged those 12 tokens once; no gate command ran. An explicit later foreground retry succeeded, bringing goal usage to 24 while the stopped driver's total stayed 12.

Additional actual HTTP receipts: Anthropic goal continuation made two requests
and charged 14 tokens; `end_turn` gate exit 0 and `stop_sequence` gate exit 7
executed actual marker commands and each charged 7 tokens. Mixed usage retained
public total 15 while charging goal budget 20. Interrupt retained the accepted
answer. Actual on-disk registered refine/rollback restored the prior learned
fact. MCP stdio initialized 108 tools and its real `read_file` response matched
the 1160-byte coding-root README on disk. Fresh isolated editable `[dev]` install,
setup and canonical repository/pinned-upstream clones succeeded.

## Deviations and fixes

- Integration exposed missing `json` composition and typed goal imports, lost terminal accounting, clear/paused-goal precedence, successful-document refusal false positives and startup-degradation veto loss. These were corrected, not hidden by fallback success.
- Typed validation now retains real verdict extras. Factory capture, optional boundary reason and literal-false context exits satisfy mypy without casts or suppression of product errors.
- Parent-owned README, CHANGELOG and loop/connector/migration docs describe exercised behavior. Five earlier continuation-owned files received formatting-only fixes after session-history ownership was established; no new native architecture was added in this phase.
- Incidental registration/wording/length assertions were removed rather than repinned. The real scheduler wall-clock due-now check remains a throwaway smoke, not a permanent timing-sensitive test.
- The remaining three `test_prime_pin.py` assertions tested static defaults/schema/doc substrings rather than a consumer operation; the obsolete module was removed. Current source-policy smoke, authoritative pinned checkout, native build, license and CI checks preserve actual provenance evidence. The prior 689-test receipt remains historical in the evidence matrix; the final full suite is 686.
- Independent source reviews produced 14 findings: 12 fixed, two retained producer/locked-contract semantics with explicit documentation; see `61-REVIEW.md`. Sticky autonomous stop remains authoritative until explicit `autonomous_start`; incomplete driver stop codes never imply `completed: true`.
- Nine missing native source license headers, root tracked license policy and independent native build/license CI were added; `ai.rs` already carried its license header. No Rust function/ABI or ignored upstream source changed. Broken clone/project/issue URLs were corrected.
- REPO-04 is reopened rather than falsely marked met: source-only Cargo dependency resolution exits 101 because ignored required upstream path manifests are absent. Plain `--no-deps` metadata exits 0 but is not dependency-resolution proof. Cargo automation needs a user-approved source cutover or explicit scope exception.

## Threat Flags

No new unmitigated implementation threat identified during execution. Planned privilege/refusal, unbounded-continuation, stale-state and secret-disclosure controls have exercised behavior evidence. The parent-owned security report records the formal dispositions; no risk acceptance is claimed here.

## Task Commits

No phase implementation commit or publication has occurred yet. Executors were explicitly prohibited from committing; parent shipping remains behind review, verification, audit and ownership gates. `commit_docs: false` remains in force.

## Limitations / Next Gate

The ignored upstream Rust logic remains unchanged. Its retained accounting is exit 101: 5089 passed, two known local ext4 failures, 19 ignored, three filtered; it was not rerun or relabeled green. Native bridge headers were rebuilt and license-checked successfully. Milestone audit, the REPO-04 decision and authorized archive/cleanup remain required; this implementation summary does not claim archival completion.
