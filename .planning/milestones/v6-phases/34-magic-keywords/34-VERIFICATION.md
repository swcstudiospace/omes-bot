---
status: passed
---

# Verification 34: Magic keywords

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_magic_keywords.py -q` → exit 0, 5 passed
  (table, matching goldens, masking, gating/switches, loop injection).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 224 passed (219 + 5).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- Differential check vs Omp's own matcher: 0 mismatches.

## Requirements

- KEY-01, KEY-02: Done.
