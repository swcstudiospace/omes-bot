---
status: passed
---

# Verification 23: Red-team depth

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_pyrit_target.py -q` → exit 0,
  3 passed (five-case adversarial battery through the real PyRIT send path
  with an empty canary log, approved-control payload, assistant message shape).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 144 passed (141 + 3).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- PyRIT memory is in-memory SQLite: no model keys, no files, no network.

## Requirements

- RT-01, RT-02: Done.
