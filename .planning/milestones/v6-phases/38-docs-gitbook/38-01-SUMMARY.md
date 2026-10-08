# Summary 38-01: Docs set, summary, sync guide

## What shipped

`docs/` (new, 6 pages): README (audience router), setup
(installer guide + smoke + troubleshooting), user-guide (magic
words, ultrathink turns, skills, tools/approvals, receipts),
build-aesthetics (one process, packs, contracts, seams/fakes/
receipts, guards, layout — all counts verified), tool-host
(server flags, OpenShell, AgentOS), gitbook-sync (dashboard
connection guide). `.gitbook.yaml` (verified keys) +
`docs/SUMMARY.md` (each file once). `omega_prime/tests/test_docs.py`
(new, 2 tests): SUMMARY resolves exactly once, config + headings
present. Every doc claim verified against the codebase
(paths, counts 26/5/104/235/21, `XAI_API_KEY`, CLI flags);
invented token env names corrected in both setup docs.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_docs.py -q` → exit 0, 2 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 235 passed (233 + 2).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
