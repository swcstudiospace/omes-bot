# Summary 26-01: Lead core+lead tool families

## What shipped

`omes/tools/lead.py`: 16 registry tools porting desk `core.py` + `lead.py`
(brief, docs search, memory retain/recall, ownership, receipt check, events,
doctor, render prompt, intake next/ack, graph register/state, bus start/wait,
roster status) behind `LeadContext` with JSON stores and injected substrate/
bus/docs/notify seams. Memory reuses Omes `MemoryStore` via banked
`Hindsight`; receipts reuse `validate_receipt`; ownership parses the Omes
manifest. Eight state-changing tools require approval.

Roster, shipped policy, and the three composition assertions extended with
the 16 names.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_lead.py -q` → exit 0, 10 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 177 passed (167 + 10).

## Follow-ups

- 26-02: lead routine, skill, red-team eval cases.
