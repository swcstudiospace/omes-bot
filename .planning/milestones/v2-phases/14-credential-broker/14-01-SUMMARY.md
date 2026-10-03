---
phase: 14-credential-broker
plan: 01
subsystem: credentials
tags: [broker, credentials, redaction]
provides:
  - Env-backed per-endpoint keys plus redaction in logs, events, recall
affects: [15-durable-runs]
---

# Phase 14 summary

`CredentialBroker` resolves provider keys from an injected env mapping only after the seat policy approves the request host; refusals and missing keys raise `ProviderError` before the transport is touched. `ProviderModel` with a broker builds the request once to learn the URL, resolves the key, and rebuilds — adapters untouched, brokerless behavior unchanged. `redact_text` covers `sk-`/`xai-`/GitHub/AKIA patterns, Bearer values, and key assignments plus caller-known secrets; the broker's own `redact` covers resolved keys without exposing them. Audit reasons, event payloads, and model-facing memory recall are stored redacted.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `105 passed in 3.58s` (`test_credentials.py`: 5 passed)

Unverified: secret managers beyond the environment, live endpoints, the phase 16 transport allowlist.
