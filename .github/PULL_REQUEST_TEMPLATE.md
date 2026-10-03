<!-- One concern per PR. Fill every section. -->

## Summary

## Behavior change

## Verification

Commands + exit codes (all four gates):

- [ ] `.venv/bin/python -m pytest omes/tests -q`
- [ ] `.venv/bin/python -m omes.evals.runner omes/evals/cases`
- [ ] `bash omes/scripts/assemble-prompts.sh --check`
- [ ] `.venv/bin/python -m omes.setup_check --root .`

## Contracts touched

<!-- Roster, policy, template, skills, routines, docs — list each file or "none". -->

## Secrets check

- [ ] No secrets, tokens, or private URLs in this PR.
