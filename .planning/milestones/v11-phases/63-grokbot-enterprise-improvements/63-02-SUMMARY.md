---
phase: 63-grokbot-enterprise-improvements
plan: "02"
subsystem: grokbot-credentials
tags: [tokens, scopes, revocation, fail-closed, cli]
requires:
  - phase: 62
    provides: `TokenStore`, `Principal`, scopes, `atomic_write_json`
provides:
  - Hashed, scoped, expiring, revocable token file
  - `FileTokenStore` with live reload that fails closed
  - `python -m omega_prime.grokbot.tokens new|list|revoke`
affects: [63-08, 63-06]
tech-stack:
  added: []
  patterns: [subclass of the existing store, sidecar flock, fail-closed degraded state]
key-files:
  created:
    - omega_prime/grokbot/tokens.py
    - omega_prime/tests/test_grokbot_tokens.py
key-decisions:
  - "Only the SHA-256 is stored; the plaintext is shown once by `new` and never written."
  - "An unreadable, corrupt or wrong-version file denies everyone and reports `degraded`; a later good file clears it. A single malformed record degrades the whole file."
  - "`create_token`/`revoke_token` refuse to touch a corrupt file instead of overwriting it."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-02 Scoped, rotatable credentials

Commit `fa5a22b`. Requirement: GRI-02.

`FileTokenStore` stats the file at most once per `reload_interval`, reloads when `(mtime_ns, size)` changes
and compares the presented token against every valid record in constant time. Expired (`clock() >= expires_at`)
and revoked tokens are refused on the very next request, with no restart. `CompositeTokenStore` lets a file
store sit next to the single env/file bearer token. 23 tests, including an `AuthMiddleware` integration where a
token works, is revoked and then gets 401.
