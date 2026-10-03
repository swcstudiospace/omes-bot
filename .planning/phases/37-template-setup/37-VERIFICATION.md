---
status: passed
---

# Verification 37: Template + setup

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_setup_check.py -q` → exit 0, 2 passed
  (green run, per-check failure trips).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 233 passed (231 + 2).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omes.setup_check --root .` → exit 0.

## Requirements

- TPL-01, TPL-02: Done.
