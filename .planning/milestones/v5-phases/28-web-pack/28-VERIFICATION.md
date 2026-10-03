---
status: passed
---

# Verification 28: Web pack

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_web.py -q` → exit 0, 6 passed
  (allowlist + shapes, preview shape/mismatch/failure, scan findings,
  review orchestration + vision tolerance, browser lifecycle, approvals).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 193 passed (187 + 6).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- WEB-01, WEB-02, WEB-03: Done.
