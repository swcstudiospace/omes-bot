# Testing: desk gates + Omes gates for the port

## Desk gates (port as Omes eval/CI checks)

- `check_receipt.py` (G-2): receipt shape + exit-code grounding — the gate
  to mirror most closely in Omes evals.
- `check_contracts.py`, `check_desk_integrity.py`, `check_ownership.py`,
  `check_rollback.py`, `check_secrets.py`, `run_all.py`.
- Gateway `tests/` (224K): read the per-tool tests as the behaviour spec
  when porting each tool family.

## Omes gates (every v5 phase must pass)

- `.venv/bin/python -m pytest omes/tests -q` → exit 0 (currently 167).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0 (6/6).
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
- New pack behaviour: focused `omes/tests/test_<pack>.py` with fake peers;
  new refusal/contract behaviour: `omes/evals/cases/<pack>.json` entries.
- Roster/policy/template composition tests must be extended with each pack
  (v4 Phase 25 precedent: `test_tools/test_growth/test_providers/test_policy`).
