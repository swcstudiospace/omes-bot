---
status: passed
---

# Verification 31: Quality pack

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_quality.py -q` → exit 0, 11 passed
  (gate aggregation incl. failure, Greptile actions + unconfigured, approve
  stamp + self/invalid/missing/path refusals, waiver shape, ack lifecycle +
  coverage, supply-chain goldens, scan findings + path guard, registration +
  approvals via dispatch).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 214 passed (203 + 11).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 8 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- QUA-01, QUA-02, QUA-03: Done.
