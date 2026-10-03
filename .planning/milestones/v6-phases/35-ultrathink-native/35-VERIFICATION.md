---
status: passed
---

# Verification 35: Ultrathink native

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_ultrathink.py -q` → exit 0, 3 passed
  (bridge verbs + argv, unconfigured/failure/approval edges, plan resolution).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 227 passed (224 + 3).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- ULT-01, ULT-02: Done.
