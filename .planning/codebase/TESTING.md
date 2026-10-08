# Testing: desk gates + Omega Prime gates for the port

## Desk gates (port as Omega Prime eval/CI checks)

- `check_receipt.py` (G-2): receipt shape + exit-code grounding — the gate
  to mirror most closely in Omega Prime evals.
- `check_contracts.py`, `check_desk_integrity.py`, `check_ownership.py`,
  `check_rollback.py`, `check_secrets.py`, `run_all.py`.
- Gateway `tests/` (224K): read the per-tool tests as the behaviour spec
  when porting each tool family.

## Omega Prime gates (every v5 phase must pass)

- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0 (currently 167).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0 (6/6).
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- New pack behaviour: focused `omega_prime/tests/test_<pack>.py` with fake peers;
  new refusal/contract behaviour: `omega_prime/evals/cases/<pack>.json` entries.
- Roster/policy/template composition tests must be extended with each pack
  (v4 Phase 25 precedent: `test_tools/test_growth/test_providers/test_policy`).
