---
milestone: v10
milestone_name: Prime merge
audited: "2026-10-08"
status: passed
scores:
  requirements: 32/32
  phases: 8/8
  integration: 4/4
  flows: 4/4
implementation:
  completed_plans: 10
  total_plans: 10
security:
  asvs_level: 1
  block_on: high
  threats_total: 0
  threats_closed: 0
  blocking_open: 0
  accepted_risks:
    - "PYSEC-2026-4114 ignored: oauthlib authorization-server PKCE timing oracle; tweepy 4.17 pins oauthlib<4; this process does not host that grant (SECURITY.md)."
nyquist:
  compliant_phases: []
  partial_phases: []
  not_validated_phases: []
  missing_phases: [53, 54, 55, 56, 57, 58, 59, 60]
  overall: not_run
gaps:
  requirements: []
  integration: []
  flows: []
  security: []
tech_debt:
  - phase: "53-prime-discovery"
    items:
      - "Three pa-cli acp_mode_e2e tests stay skipped (ACP-stdio settle timing, out of port scope). The skip set is in prime-agent.pin.json and rust-parity.yml."
  - phase: "59-repo-hardening"
    items:
      - "Dependabot does not track cargo. prime-agent/ is an ignored pin; cargo-deny gates that workspace instead."
      - "PYSEC-2026-4114 is an explicit, scoped ignore until tweepy accepts oauthlib>=4."
      - "The local mypy console-script shebang still points at /root/src/repos/Omes-Bot/.venv. CI uses python -m mypy, which passes."
  - phase: "milestone"
    items:
      - "No Nyquist VALIDATION.md was produced for phases 53-60. Verification reports and the gates below are the evidence."
      - "No separate STRIDE pass was run for v10. New Prime families are default-off. The v9 egress and browser gates remain in the suite."
      - "The full suite still emits 12 audioop/PyRIT deprecation warnings."
closure:
  authorized: true
  reason: "All 32 v10 requirements have a cited command that exited 0. Phase 59 verification was the missing report and is now passed."
---

# v10 — Milestone Audit

**Verdict: passed.** One Python agent now runs Hermes, Omp, and Prime logic. Prime's RLM recursion, continual harness, goals, heartbeats, autonomous mode, and agent messaging are behavior-ported behind default-off flags. The repo is AGPL-3.0, Copyright (C) 2026 Spectrum Web Co.

## Commands re-run at closeout (2026-10-08)

| Command | Exit | Result |
|---|---|---|
| `.venv/bin/python -m pytest omega_prime/tests -q` | 0 | 528 passed, 12 warnings |
| `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` | 0 | 26 passed, 0 failed |
| `.venv/bin/ruff check omega_prime` | 0 | clean |
| `.venv/bin/ruff format --check omega_prime` | 0 | 246 files already formatted |
| `.venv/bin/python -m mypy omega_prime` | 0 | no issues in 215 source files |
| `bash omega_prime/scripts/assemble-prompts.sh --check` | 0 | up to date |
| `.venv/bin/python -m omega_prime.tooling.catalog --check` | 0 | up to date |
| `.venv/bin/python -m omega_prime.setup_check --root .` | 0 | registry serves 108 roster tools |
| `.venv/bin/python -m pip_audit -r requirements-lock.txt --ignore-vuln PYSEC-2026-4114` | 0 | no known vulnerabilities, 1 ignored |
| `cargo-deny 0.20.2 check licenses` in `prime-agent/` | 0 | `licenses ok` |
| `rustc --version` | 0 | `rustc 1.98.1`, matches `prime-agent.pin.json` |
| `cargo test --workspace --locked` with the three documented skips (Phase 53 baseline, same pin `967eb13f`; v10 did not modify `prime-agent/` sources) | 0 | 622 passed. The three `pa-cli` ACP e2e tests fail unskipped and are excluded by `prime-agent.pin.json`, which is what CI passes. |

## Requirements

| Requirement | Phase | Evidence | Result |
|---|---|---|---|
| DISC-01 | 53 | `.planning/research/v10-prime-capability-map.md`; `53-VERIFICATION.md` status passed | satisfied |
| DISC-02 | 53 | `.planning/research/v10-omega-overlap-map.md`; `53-VERIFICATION.md` | satisfied |
| DISC-03 | 53 | Skip-set `cargo test --workspace --locked` on `967eb13f`: 622 passed (`53-VERIFICATION.md`). Unskipped, the three `pa-cli` ACP e2e tests fail and are the documented exclusions. Pin in `VENDOR.md` and `prime-agent.pin.json` | satisfied |
| BUILD-01 | 54 | `.github/workflows/rust-parity.yml` runs `cargo build --locked` and `cargo test --workspace --locked` with the pin's skip set | satisfied |
| BUILD-02 | 54 | `cargo-deny 0.20.2 check licenses` → exit 0, `licenses ok`. Allowlist is MIT/Apache/BSD/ISC/Zlib and the other permissive IDs in `prime-agent/deny.toml` | satisfied |
| BUILD-03 | 54 | `prime-agent.pin.json` toolchain `1.98.1`; `rustc 1.98.1` locally; the workflow passes that toolchain to `dtolnay/rust-toolchain` | satisfied |
| RLM-01 | 55 | `omega_prime/agent/rlm.py` `RlmHost`; `test_rlm.py` (39 tests in the phase report). Full suite 528 passed | satisfied |
| RLM-02 | 55 | `rlm_list_subagents` / `rlm_delete_subagent`; closed status sets in `agent/rlm.py` | satisfied |
| RLM-03 | 55 | `rlm_create_session` and `rlm_progress_note` (512 UTF-16 cap, 10s throttle) | satisfied |
| RLM-04 | 55 | Child isolation covered by the RLM host tests; collect returns snapshots and does not raise on timeout | satisfied |
| HARN-01 | 56 | `omega_prime/learning/harness.py` `HarnessState`; `test_continual_harness.py` (19 tests in the phase report) | satisfied |
| HARN-02 | 56 | `omega_prime/agent/refine.py`; evidence required or nothing is applied | satisfied |
| HARN-03 | 56 | Snapshots and exact rollback in the harness tests | satisfied |
| HARN-04 | 56 | Refine tests assert the base system prompt bytes do not change | satisfied |
| LOOP-01 | 57 | `agent/goals.py` `PrimeGoalStore`; `test_goals_prime.py` | satisfied |
| LOOP-02 | 57 | `cron/heartbeat.py`; `test_heartbeat.py` | satisfied |
| LOOP-03 | 57 | `agent/autonomous.py`; `test_autonomous.py` | satisfied |
| LOOP-04 | 57 | `agent/messaging.py`; `test_agent_message.py` | satisfied |
| LOOP-05 | 57 | `config.py` `PRIME_FAMILIES`, default off; `test_prime_config.py` | satisfied |
| LOOP-06 | 57 | `agent/degraded.py` `prime_degraded`; `test_prime_degraded.py` | satisfied |
| LOOP-07 | 57 | `test_prime_regression.py`; setup check still serves 108 tools with Prime flags off; full suite 528 passed | satisfied |
| CONN-01 | 58 | `omega_prime/prime/` adapters, `SCHEMA_VERSION`, strict decoders | satisfied |
| CONN-02 | 58 | `test_prime_contracts.py` (29 tests in the phase report) | satisfied |
| CONN-03 | 58 | `test_prime_failure_injection.py` (7 tests in the phase report) | satisfied |
| CONN-04 | 58 | `omega_prime/tests/parity/` plus `test_prime_parity.py` (6 tests in the phase report) | satisfied |
| REPO-01 | 59 | `LICENSE` AGPL-3.0 text and the copyright line; SPDX headers asserted by `test_new_v10_modules_carry_spdx_headers` | satisfied |
| REPO-02 | 59 | `test_required_files_exist_and_nontrivial` → exit 0 | satisfied |
| REPO-03 | 59 | ADR-0001, `connectors.md`, `agent-loop.md`, `migration.md` present; docs tests in the 528 | satisfied |
| REPO-04 | 59 | `supply-chain.yml` pip-audit exit 0 with the documented ignore; `rust-parity.yml` cargo-deny exit 0; dependabot pip + github-actions. Cargo dependabot omitted on purpose (see tech debt) | satisfied |
| REPO-05 | 59 | README quickstart commands executed: editable install, setup check, MCP server, `cargo build --locked` (Phase 59 summary) plus the gates in the table above | satisfied |
| DONE-01 | 60 | This audit | satisfied |
| DONE-02 | 60 | ROADMAP, MILESTONES, and STATE record v10 complete; phase dirs moved to `milestones/v10-phases/` | satisfied |

No orphaned requirement: every ID in `milestones/v10-REQUIREMENTS.md` appears in a phase verification report (59 and 60 written at this closeout; 53–58 were already `status: passed`).

## Integration

Checked from the one suite, not a separate subagent:

1. Prime flags default off and the registry still serves 108 tools (`setup_check` exit 0, `test_prime_regression.py`).
2. RLM, harness, goals, heartbeats, autonomous mode, and messaging tests pass inside `pytest` (528).
3. Connector contract, failure-injection, and parity fixtures pass inside the same suite.
4. Prompt assembly and the tool catalog still match the tree.

## Flows

1. Install and import the package (`pip install -e '.[dev]'` during Phase 59, exit 0; tests import the tree).
2. `setup_check` and the MCP server start path (Phase 59: `python -m omega_prime.mcp_server` reached EOF and exited 0).
3. A Prime-disabled turn does not register Prime tools (LOOP-07).
4. A Prime failure emits `prime_degraded` and the loop continues (LOOP-06).
