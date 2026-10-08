# Summary 26-02: Lead routine, skill, evals

## What shipped

`omega_prime/routines/desk_lead.py`: `run_lead_pass` claims bounded intake batches,
tickets each order, dispatches through an injected dispatcher, acks from
validated receipts, and consolidates a plain-text report. Missing dispatcher,
missing receipts, and invalid receipts block the ticket and reopen the order;
a per-pass seen-set keeps reopened orders from looping. Todos mirror tickets.

`omega_prime/skills/lead-pack/SKILL.md`: pass procedure, ticket shape, dispatch and
receipt rules, tool list.

Eval note (deviation from plan): no `redteam.json` additions. Registry eval
cases use canned stubs, so a canned `lead_bus_start` case could not guard the
real approval flag; refusal coverage lives in `test_lead.py`, which dispatches
the real registration through `ApprovalLog`.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_desk_lead.py -q` → exit 0, 4 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 181 passed (177 + 4).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
