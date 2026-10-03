# Summary 31-01: Quality tools, skills, and gate mirrors

## What shipped

`omes/tools/quality.py`: 8 registry tools porting desk `quality.py` (gates
run, Greptile trigger/get/comments, receipt approve, waiver record, contract
ack/status, supply-chain check, secret scan). Approvals and waivers are
stamped and written under the root; Omes never pushes. Approval on greptile,
approve, waiver, ack (desk write kinds). Greptile, the command runner, and
VCS are injected seams; tests use fakes only. Contract proposals read from
`contracts/changes/<id>.json` (Omes has no YAML parser). Secret scan reuses
the credentials redactor over given files (default: whole tree, max 2000).

`omes/evals/cases/redteam.json`: 2 gate-mirror cases (unapproved
`qua_receipt_approve` refused, policy-forbidden `qua_greptile_review`
refused). Registry cases use stubs, so they assert refusal machinery;
logic-level refusals are unit-tested; the gates themselves run via
`qua_gates_run`.

`omes/skills/{code-review,debugging,security-secrets-handling,security-supply-chain}/SKILL.md`:
desk skills with `bots:` repointed. Roster, policy, composition extended;
shipped-cases assertion raised 6 → 8.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_quality.py -q` → exit 0, 11 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 214 passed (203 + 11).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 8 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
