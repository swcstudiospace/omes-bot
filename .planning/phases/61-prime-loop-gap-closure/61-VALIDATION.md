---
phase: "61"
slug: prime-loop-gap-closure
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-10-08
---

# Phase 61 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | Existing pytest in repository venv |
| Configuration | `pyproject.toml` / existing test fixtures |
| Quick run | `.venv/bin/python -m pytest omega_prime/tests/test_prime_loop.py omega_prime/tests/test_heartbeat_runtime.py -q` |
| Full suite | `.venv/bin/python -m pytest omega_prime/tests -q` |
| Observed affected latency | 7.42 seconds; 234 passed in the 15-file affected suite |
| Observed full latency | 30.66 seconds; 686 passed after retiring three static source-pin tests, 12 dependency warnings |

## Sampling Rate

- Original01/02 execution units ran concurrently with disjoint ownership and no worker checks/commits. Parent smoke and recorded234/686 gates ran after those workers were idle.
- The exact broader integration audit subsequently found10 literal requirement gaps; old sampling instructions and test success do not prove all consumers or historical/clean-environment criteria.
- Bounded03/04/05 repairs are executing; parent06 final current evidence waits for the integrated wave. No mid-flight run is relabeled a final gate.
- Before updated verification: full suite and actual changed consumer smoke must pass, including durability/progress/privacy, typed failures, conditional prompt, historical fixture and isolated pinned checkout.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| 61-01-01 | 01 | 1 | LOOP-01, LOOP-05, LOOP-07 | T-61-02, T-61-04 | Fresh goal state and bounded continuation; literal prompt/history gaps reopened | integration | `.venv/bin/python -m pytest omega_prime/tests/test_prime_loop.py -q` | yes | LOOP-01 green; LOOP-05/07 gaps found |
| 61-01-02 | 01 | 1 | LOOP-01, LOOP-03, LOOP-06 | T-61-03, T-61-04, T-61-06 | Correct terminal precedence, real gate outcome, once-only paid accounting and redacted non-extending failure | integration | `.venv/bin/python -m pytest omega_prime/tests/test_prime_loop.py omega_prime/tests/test_goals_prime.py omega_prime/tests/test_autonomous.py omega_prime/tests/test_prime_contracts.py omega_prime/tests/test_prime_degraded.py omega_prime/tests/test_prime_failure_injection.py -q` | yes | green |
| 61-01-03 | 01 | 1 | LOOP-04, LOOP-05, LOOP-07 | T-61-01, T-61-05 | Same registry ownership and foreground fast-fail; literal prompt/history gaps reopened | integration | `.venv/bin/python -m pytest omega_prime/tests/test_prime_loop.py omega_prime/tests/test_loop.py omega_prime/tests/test_prime_config.py omega_prime/tests/test_agent_message.py -q` | yes | LOOP-04 green; LOOP-05/07 gaps found |
| 61-02-01 | 02 | 1 | LOOP-02, LOOP-06 | T-61-02-01, T-61-02-02, T-61-02-04 | Named wait outside bookkeeping locks; malformed/unknown jobs fail honestly; nonserializable outcomes are redacted errors | integration | `.venv/bin/python -m pytest omega_prime/tests/test_heartbeat_runtime.py -q` | yes | green |
| 61-02-02 | 02 | 1 | LOOP-02 | T-61-02-03, T-61-02-06, T-61-02-07 | Claim/finish reconciliation, no clear resurrection/overlap, bounded history, conditional detach, settled/retryable/latest-stop shutdown | integration | `.venv/bin/python -m pytest omega_prime/tests/test_heartbeat_runtime.py -q` | yes | green |
| 61-02-03 | 02 | 1 | LOOP-02, LOOP-06 | T-61-02-04, T-61-02-07 | Actual tool set/list/clear behavior and owning-session degradation; generic cron neighbors preserved | integration | `.venv/bin/python -m pytest omega_prime/tests/test_heartbeat_runtime.py omega_prime/tests/test_apscheduler_backend.py omega_prime/tests/test_heartbeat.py -q` | yes | green |

The commands above were covered by the actual parent-run broader affected suite (234 passed, exit 0) and full suite, not separate fabricated invocations. Specific node selection is a sampling instruction; exact exercised commands, stdout and corrected failures are in `61-EVIDENCE.json`.

## Requirement Cross-Reference

| Requirement | Existing green consumer-behavior coverage | Production proof |
|---|---|---|
| LOOP-01 | `test_prime_loop.py`, `test_goals_prime.py` | Real native goal continuation/persisted 36-token limit; real later provider failure accounting |
| LOOP-02 | `test_heartbeat_runtime.py`, unchanged heartbeat/cron suites | Real APScheduler/native named-agent lease waiting, reentrant clear, history and settled threads |
| LOOP-03 | `test_prime_loop.py`, `test_autonomous.py` | Real turn/token/time limits, real argv pass/fail commands and no gate on terminal provider failure |
| LOOP-04 | Unmodified `test_agent_message.py` | Existing rostered messaging regression preserved |
| LOOP-05 | Default-off live registrations covered, but static prompt/roster leaked names | Before actual render contains disabled rlm_spawn; Plan05 repair awaits final smoke |
| LOOP-06 | Loop/heartbeat/degraded/failure-injection suites | Real hook failure and real HTTP-400 beat error, redacted and correctly routed; normal foreground remains usable |
| LOOP-07 | Prior synthetic assertions were not a historical fixture | Real79ff51af source captured six transcripts; current comparator and unmodified pre-v10 suite against current code wait for integration |
| HARN-03 / HARN-04 (parent audit repair) | Actual registered refine/rollback plus fixed-prompt agent-turn regression in `test_continual_harness.py` | Real durable before/after rollback proof; prior entry restored |
| REPO-01 / REPO-02 / REPO-03 / REPO-05 (parent source audit) | Existing public-link/GitBook checks and narrow source-policy smoke retained | Native headers/build/licenses/install/MCP observed; isolated full-suite prerequisite failure reproduced, corrected quickstart/CI await isolated after run |

## Wave 0 Requirements

Existing pytest infrastructure is reused. Original six tasks have recorded narrow gates; new03–06 behavior repairs and nine additional threat mitigations require integrated consumer smoke and final commands. Native bridge logic and ignored upstream Rust remain unchanged; known ext4 failures are not rerun.

## Manual-Only Verifications

None for the seven implementation requirements. No UI or human-judgment surface changed. The throwaway native probes were actual executable integration checks, not manual-only substitutions; their observed receipts are retained in the summaries and Linear SPE-8277 before deletion.

REPO-04 Cargo automation and DONE-01/DONE-02 lifecycle closeout remain blocked, not manual-only behavioral test gaps. Cargo dependency resolution from repository-fetchable source exits 101 on an ignored required path; a source-packaging change or explicit scope exception requires a user decision. Audit, authorized archive/cleanup and state evidence remain required. Nyquist compliance here covers implementation behavior, not permission to claim milestone completion.

## Validation Sign-Off

- [x] All six tasks declare automated verification.
- [x] No three consecutive tasks lack a verification command.
- [x] Existing infrastructure covers all referenced files; Wave 0 complete.
- [x] No watch-mode flags or permanent native wall-clock smoke tests.
- [x] Real runtime and scheduler smoke plus final affected/full/static gates observed passing.
- [x] No uncovered implementation requirement or newly accepted manual-only gap.
- [x] `nyquist_compliant: true`; `status: validated`.

**Approval:** Validated 2026-10-08 by parent integration owner. The first independent source review (`61-REVIEW-pre-repair.md`) found 2 critical and 14 warning findings, all repaired or consciously retained; the post-repair review (`61-REVIEW.md`) has no open findings; all five production behavior criteria are exercised. Canonical phase verification remains `human_needed` at the REPO-05/lifecycle gate; no unavailable signed specialist gate is claimed.

## Validation Audit 2026-10-08

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## Post-repair validation (2026-10-09)

The expanded cross-phase gate above was the pre-repair state. After plans 61-03..06 and the
review-repair wave every implementation requirement has automated consumer-behavior coverage
and a production-path receipt; the independent final 32-ID check
(`61-INTEGRATION.md`: 27 wired, 3 broken, 2 human-needed) and the user's 2026-10-09 decisions
(LOOP-07 and REPO-04 exceptions, CONN-01 documented scope, stop before lifecycle) are recorded
in `.planning/v10-MILESTONE-AUDIT.md`.

| Behavior (requirement) | Automated command | Result |
|---|---|---|
| Full suite | `.venv/bin/python -m pytest omega_prime/tests -q` | 980 passed |
| Static gates | `ruff check`, `ruff format --check`, `mypy omega_prime/` | 0 / 0 / 0 (245 sources) |
| Evals, assembly, catalog, setup | `omega_prime.evals.runner`, `assemble-prompts.sh --check`, `tooling.catalog --check`, `setup_check` | 26 passed / up to date / up to date / exit 0 |
| Malformed tool-call arguments are error rows; refusal scope (CONN-03, LOOP-03) | `pytest omega_prime/tests/test_prime_loop_boundaries.py` | 13 passed |
| Bound messaging identity (LOOP-04, CONN-01) | `pytest omega_prime/tests/test_agent_message.py` | passed |
| Declared-only typed tool surface, all seven families (CONN-01) | `pytest omega_prime/tests/test_prime_tool_surface.py test_prime_goal_surface.py test_prime_rlm_surface.py test_prime_heartbeat_boundary.py test_prime_kernel_boundary.py` | passed |
| Policy -> approval -> decode order and audit verdicts (CONN-01, CONN-03) | `pytest omega_prime/tests/test_prime_tool_authorization.py` | 24 passed |
| RLM parent contract, durability, privacy, concurrency (RLM-03, RLM-04) | `pytest omega_prime/tests/test_rlm.py test_prime_kernel_host.py test_prime_failure_injection.py test_prime_parity.py` | passed (12 parallel stress repetitions clean) |
| Assembler output rule (LOOP-05) | `pytest omega_prime/tests/test_shell.py` | passed |
| Reviewed-defect probe (17 defects) | `phase61-probe/probe.py` on pre-repair snapshot vs repaired tree | 17 present before, 0 after |
| Real stdio MCP smoke | `phase61-probe/mcp_smoke.py` | 16/16 checks |
| Historical suite replay | `79ff51af` tests and data with current Python | 376 passed / 2 failed, identical before and after the wave (user-approved exception) |

Receipts and commands are retained in `61-EVIDENCE.json#review_repair_wave`. Nyquist compliance
here covers implementation behavior; REPO-05, DONE-01 and DONE-02 remain open lifecycle gates and
no milestone completion is claimed.
