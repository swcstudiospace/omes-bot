# Summary 40-01: Hindsight service client + fallback

## What was built

- `omega_prime/memory/hindsight_service.py`: `HindsightService` speaking the live
  hindsight-api v0.9.1 contract (retain/recall/reflect/knowledge-page search
  on the shared `ultrathink` bank) with a brokered Bearer token
  (`HINDSIGHT_API_KEY`, `HINDSIGHT_API_TOKEN` fallback) and plugin-parity
  recall defaults (`observation` types, `low` budget). The client is truthful:
  transport/auth/malformed failures raise `HindsightError`.
- `omega_prime/memory/hindsight_bridge.py`: `HindsightBridge` keeping the local
  `Hindsight` call shapes with service-first, local-on-`HindsightError`
  fallback; reflect/pages degrade to empty.
- `omega_prime/tests/test_hindsight_service.py`: 13 tests — route/body shapes,
  refusal mapping, blank-skip parity, fallback matrix, bank/URL validation,
  token-leak guard.

## Verification

`.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 270 passed
(257 carried + 13 new). No network in tests. No new dependencies.
