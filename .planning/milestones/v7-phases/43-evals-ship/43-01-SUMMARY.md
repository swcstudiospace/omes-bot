# Summary 43-01: Probes, evals, template, docs

## What was built

- Eval cases `golden-substrate-claim-approved` + `redteam-substrate-claim-unapproved`
  (machinery pattern); suite is 23/23.
- `omega_prime/substrate/probes.py`: read-only manual probes (substrate `/healthz` +
  `/brief`, hindsight `/health` + `/version`) with env config, secret-free
  reports, exit 0 iff all pass. Never runs in CI.
- `setup_check` gains the `substrate` check (skip when unwired, fail on
  malformed URLs, names set variables without values).
- Template Description names the surface (bullet sections stay empty);
  SETUP.md gains the two token rows + URL defaults; `docs/substrate.md`
  guide listed once in SUMMARY.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 294 passed (288 + 6 new).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 23 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omega_prime.setup_check --root .` → exit 0 (substrate skips unwired).
- Manual `.venv/bin/python -m omega_prime.substrate.probes` → exit 1 with brief
  ok (113 chars), hindsight health/version ok, substrate health FAIL on
  HTTP 503: the local substrate-mcp has no ledger/index attached, so its
  own `healthStatus` reports 503 by design. Reads pass; the probe reports
  the degraded writer truthfully. No secrets printed.
