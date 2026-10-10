---
phase: 63-grokbot-enterprise-improvements
plan: "03"
subsystem: grokbot-approvals
tags: [approvals, admin-api, ttl, audit]
requires:
  - phase: 62
    provides: Scope hierarchy, audit chain, `ApprovalLog`
provides:
  - TTL, revoke and entries on `ApprovalLog` (backward compatible, thread-safe)
  - Admin-scoped `/admin/approvals` API with audit events
affects: [63-08, 63-06]
tech-stack:
  added: []
  patterns: [admin scope gate, strict body parsing, bounded TTL]
key-files:
  modified:
    - omega_prime/tools/approvals.py
  created:
    - omega_prime/grokbot/approvals_api.py
    - omega_prime/tests/test_approvals_ttl.py
    - omega_prime/tests/test_grokbot_approvals_api.py
key-decisions:
  - "A TTL above the cap is rejected (422), never silently clamped; zero, negative and non-finite TTLs are errors."
  - "The approver is the admin principal (`label or id`); the log's own rule that the bot cannot approve itself surfaces as 403."
  - "Audit writes run in a worker thread; a failed audit write logs a warning and never changes the HTTP result."
  - "Revoking an already-expired approval is a 404."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-03 Human approval gateway

Commit `bbe25f0`. Requirement: GRI-03.

Before this, an approval-gated tool (deploys, publishes, merges, tracker writes) could only be approved by
restarting the host with `--approve`. Now an admin token calls `POST /admin/approvals` with a tool name and an
optional TTL, `GET` lists current approvals, and `DELETE /admin/approvals/{tool}` revokes. A `call`-scope token
gets 403; non-gated and unknown tools get 404; bodies are limited to 4096 bytes. All 906 pre-existing tests that
mention approvals pass unmodified. 43 new tests.
