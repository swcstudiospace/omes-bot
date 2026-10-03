---
status: passed
---

# Verification 33: Hardening

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_receipts_e2e.py -q` → exit 0, 2 passed
  (real-command citations + negatives, destructive approvals + stamp/refusal).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 219 passed (217 + 2).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- HRD-01, HRD-02: Done.
