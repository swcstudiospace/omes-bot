---
status: passed
---

# Verification 26: Lead pack

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_lead.py omega_prime/tests/test_desk_lead.py -q`
  → exit 0, 14 passed (16 tool behaviours, intake round-trip, graph/bus
  passthrough, roster/doctor/render, memory/receipt/ownership/events/brief
  paths, approval gating, routine shape/limits/blocked paths).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 181 passed (167 + 14).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- Roster, shipped policy, and all composition assertions carry the 16 names.

## Requirements

- LEAD-01, LEAD-02, LEAD-03: Done.
