---
status: passed
---

# Verification 38: Docs + GitBook

## Checks (all observed this session)

- `.venv/bin/python -m pytest omes/tests/test_docs.py -q` → exit 0, 2 passed
  (SUMMARY resolution/uniqueness, config keys + headings).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 235 passed (233 + 2).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- Doc-claim audit: all paths/counts/flags/env names verified in-repo.

## Requirements

- DOC-01, DOC-02, DOC-03: Done.
