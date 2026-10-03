---
status: passed
---

# Verification 29: Mobile pack

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_mobile.py -q` → exit 0,
  7 passed (Play flows + halt edges + confirm rule, size/lint goldens,
  TestFlight/phased flows, entitlement/risk goldens, device list/review/
  act + backend errors, adb/simctl parsers, approvals).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 200 passed (193 + 7).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- MOB-01, MOB-02, MOB-03: Done.
