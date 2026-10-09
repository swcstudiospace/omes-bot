---
phase: 63-grokbot-enterprise-improvements
plan: "06"
subsystem: grokbot-verify
tags: [conformance, self-test, mcp-client, ci]
requires:
  - phase: 63
    provides: The integrated host (63-08): `/mcp`, `/manifest.json`, `/metrics`, `/admin/approvals`, request ids
provides:
  - `python -m omega_prime.grokbot.verify`: black-box conformance checker for a running host
  - `oneclick --self-test`: boot, verify, drain with SIGTERM, require exit 0
affects: [63-07, v11-closeout]
tech-stack:
  added: []
  patterns: [checks never raise, secrets never reach the report, approval round trip with no side effect]
key-files:
  created:
    - omega_prime/grokbot/verify.py
    - omega_prime/tests/test_grokbot_verify.py
  modified:
    - omega_prime/grokbot/oneclick.py
    - omega_prime/tests/test_grokbot_oneclick.py
key-decisions:
  - "A check never raises: a failure or timeout becomes `fail` with a one-line detail. Tokens are never printed, logged or placed in the report."
  - "The approval round trip grants a 30 s approval only when the tool schema lists required arguments, treats the gate as open only when the follow-up error is a pre-handler argument error, and always revokes afterwards: the verifier never executes a gated tool."
  - "Exit 0 when nothing fails, 1 on any failure, 2 when the URL is unreachable or usage is wrong. `--require-auth` turns an unauthenticated host into a failure."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-06 Live conformance verifier and launcher self-test

Commit `20a7c3b`. Requirement: GRI-06.

Checks: `health`, `ready`, `auth_required`, `auth_missing`, `auth_query_token`, `auth_invalid`,
`origin_rejected`, `request_id`, `manifest`, `metrics`; per transport (`sse`, `http`) `initialize`,
`list_tools`, `call_tool`, `unknown_tool`, `gated_tool_refused`; with an admin token `admin:scope_enforced` and
`admin:approval_roundtrip`.

## Verified on real hosts

Against a correctly configured host with an admin token: 22 pass, 0 fail, exit 0, and the token text is absent
from the JSON and text reports. Against a host with authentication off and `--require-auth`: exit 1
(`auth_required: authentication is disabled`, `auth_missing: expected 401, got 200`). An unreachable URL exits 2.
Inside the final container, run exactly as the CI workflow does, all 20 applicable checks pass. `oneclick
--self-test` exits 0 in about 10 s and leaves no process or temp file behind.
