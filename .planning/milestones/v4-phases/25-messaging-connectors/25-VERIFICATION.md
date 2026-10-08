---
status: passed
---

# Verification 25: Messaging connectors

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_telegram.py
  omega_prime/tests/test_discord.py -q` → exit 0, 17 passed (shape mapping, reply
  threading, argument validation, broker flow and pre-call refusal, approval
  gating, real peer construction without network).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 167 passed (150 + 17).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- Roster, shipped policy, and all roster-composition assertions include the
  four new tools; no live calls in tests.

## Requirements

- MSG-01, MSG-02, MSG-03: Done.
