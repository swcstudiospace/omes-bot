# Summary 37-01: Template polish, setup flow, license

## What shipped

`omega_prime/grokbot/templates/OMEGA_PRIME.md`: description gains the magic
words, the ultrathink turn, and the setup pointer; sections stay
empty per contract. `omega_prime/grokbot/SETUP.md` (new): four-step flow
(install → secrets → optional tool host → smoke prompt) with the
exact smoke prompt and expected replies. `omega_prime/setup_check.py`
(new): runnable exit-0/1 verification (roster, template, assembly,
registry-serves-roster, ultrathink configured-or-skipped);
passes live on the repo (103 roster tools).
`omega_prime/tests/test_setup_check.py` (new, 2 tests): green run plus
per-check failure trips on fixture roots. `LICENSE` (new, MIT
2026 SWC Studio) + README footer.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_setup_check.py -q` → exit 0, 2 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 233 passed (231 + 2).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omega_prime.setup_check --root .` → exit 0 (4 ok, 1 skip).
