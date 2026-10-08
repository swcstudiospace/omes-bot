# Summary 33-01: Pack evals, receipts E2E, docs

## What shipped

`omega_prime/evals/cases/redteam.json` (+6): approval-refusal case per pack
lacking one (lead, systems, web, mobile, infra, packs), mirroring the
quality case. `omega_prime/evals/cases/golden.json` (+7):
approved-behaviour case per pack (`approve: true`, `tool_called`).
Runner total 8 → 21, exit 0, deterministic (stubs only; pack logic
stays covered by fake-backed unit tests).

`omega_prime/tests/test_receipts_e2e.py` (new, 2 tests): real hermetic
commands cited by cmd + exit code; `expects_failure`, bypass-marker,
and dangling-evidence negatives; destructive receipt approved by
another operator via `ApprovalLog`; self-approval refused by both
`validate_receipt` and `qua_receipt_approve`, which stamps a foreign
receipt without pushing.

Docs: `omega_prime/README.md` pack inventory (verified tool counts) + evals
commands; `omega_prime/ARCHITECTURE.md` Domain packs section. Pinned eval
id list in `test_evals.py` extended to 21.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_receipts_e2e.py -q` → exit 0, 2 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 219 passed (217 + 2).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
