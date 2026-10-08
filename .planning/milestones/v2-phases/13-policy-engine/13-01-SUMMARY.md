---
phase: 13-policy-engine
plan: 01
subsystem: policy
tags: [policy, enforcement, advisor, audit]
provides:
  - Seat policy with dispatch/path enforcement, advisor diffs, audit log
affects: [14-credential-broker]
---

# Phase 13 summary

`SeatPolicy` loads the JSON seat policy and answers `allows_tool`, `allows_write` (explicit `**` glob matching — `pathlib` trailing-`**` is version-quirky), and `allows_host`. The registry takes an optional policy and audit log: disallowed tools are refused before approvals and handlers, and every dispatch appends one NDJSON record (`seq`, UTC `ts`, tool, verdict) with no arguments logged. The workspace takes an optional policy and its three writers refuse read-only paths before touching a byte. `diff_policy` flags added tools/hosts and removed read-only entries as expansions, and never flags narrowing. The shipped policy allows all 23 roster names, protects prompts/contracts/grokbot/ownership, and allows no hosts.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `100 passed in 3.61s` (`test_policy.py`: 6 passed)

Unverified: network enforcement (phase 16 transport), kernel drivers, fleet gateway, formal prover.
