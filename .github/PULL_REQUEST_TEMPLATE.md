<!-- One concern per PR. Fill every section. -->

## Summary

## Behavior change

## Verification

Commands + exit codes (all four gates):

- [ ] `.venv/bin/python -m pytest omega_prime/tests -q`
- [ ] `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases`
- [ ] `bash omega_prime/scripts/assemble-prompts.sh --check`
- [ ] `.venv/bin/python -m omega_prime.setup_check --root .`

## Contracts touched

<!-- Roster, policy, template, skills, routines, docs — list each file or "none". -->

## Secrets check

- [ ] No secrets, tokens, or private URLs in this PR.
