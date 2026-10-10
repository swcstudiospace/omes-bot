---
phase: 62-grokbot-native-runtime
plan: "02"
subsystem: grokbot-audit
tags: [audit, hash-chain, rotation, tamper-evidence, redaction]
requires:
  - phase: 62
    provides: Interceptor chain and `_io` helpers (62-01)
provides:
  - Hash-chained, size-rotated, 0600, multi-process-safe audit log
  - Verifier that names the first edited, removed or reordered line
  - `python -m omega_prime.grokbot.audit verify|tail`
affects: [62-05, 62-06, 63-03, 63-05]
tech-stack:
  added: []
  patterns: [append-only hash chain, sidecar flock, quarantine-and-reset on torn tail]
key-files:
  modified:
    - omega_prime/grokbot/audit.py
    - omega_prime/tests/test_grokbot_audit.py
key-decisions:
  - "The cross-process `fcntl.flock` is taken on a `<log>.lock` sidecar: the log itself is renamed on rotation and quarantine, so a lock on it would split writers across two inodes."
  - "A torn or corrupt tail is quarantined to `<name>.corrupt-<UTC>` and the new file starts with an `audit_chain_reset` record chained from the last valid hash; auditing never stops."
  - "The key name `arg_keys` is exempt from key-name redaction (the substring `key` would otherwise redact the argument-name list)."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 62-02 Tamper-evident audit log

Commit `1d444c0` (rebased: `4e5f262`). Requirement: GRK-05.

## What shipped

Records carry `seq`, `prev` and `hash = sha256(prev + canonical_json(record))`. Rotation keeps the chain
continuous across `.1 .. .N`. `verify_integrity` reports `line N: hash mismatch | prev mismatch | seq gap |
invalid JSON | torn last line`. Redaction gained JWT triplets, `omk_` tokens and Authorization/Cookie values;
non-JSON `details` values are converted to text before redaction so a secret cannot slip through `str()`.
The directory is created on first write (so `verify` and `tail` never create anything) with mode 0700 and
files 0600. `read_recent` and the previous-hash lookup read blocks from the end of the file (O(1)).

## Verified

Concurrent appends from 8 threads and from two tracer instances on one file produce one valid chain with no
duplicate `seq`. A live emulator run produced 6 records and `audit verify` exited 0 ("verified 6 audit records").
