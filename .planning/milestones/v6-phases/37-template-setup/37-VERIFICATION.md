---
status: passed
---

# Verification 37: Template + setup

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_setup_check.py -q` → exit 0, 2 passed
  (green run, per-check failure trips).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 233 passed (231 + 2).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omega_prime.setup_check --root .` → exit 0.

## Requirements

- TPL-01, TPL-02: Done.
