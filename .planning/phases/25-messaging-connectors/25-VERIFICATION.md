---
status: passed
---

# Verification 25: Messaging connectors

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_telegram.py
  omes/tests/test_discord.py -q` → exit 0, 17 passed (shape mapping, reply
  threading, argument validation, broker flow and pre-call refusal, approval
  gating, real peer construction without network).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 167 passed (150 + 17).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- Roster, shipped policy, and all roster-composition assertions include the
  four new tools; no live calls in tests.

## Requirements

- MSG-01, MSG-02, MSG-03: Done.
