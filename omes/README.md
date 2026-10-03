# Omes

The single programming bot. Prompts point at `skills/`, `contracts/tool-rosters/omes.yaml`, and `prompts/`. The Grok template in `grokbot/templates/OMES.md` lists a skill or routine only when that file exists.

Assemble the seat prompt:

```bash
omes/scripts/assemble-prompts.sh
omes/scripts/assemble-prompts.sh --check
```

From the repository root:

```bash
python3 -m pytest omes/tests
```

The Programming Desk is absorbed as seven domain packs in `tools/` (v5):
lead (16), systems (6), web (6), mobile (13), infra (7), quality (8),
app packs (9). `skills/` holds all 24 desk skills plus the native
lead-pack skill. `contracts/tool-packs/`
carries the app pack contracts; `contracts/tool-rosters/omes.yaml` and
`contracts/policies/omes.json` list exactly what the registry offers.

```bash
.venv/bin/python -m pytest omes/tests -q
.venv/bin/python -m omes.evals.runner omes/evals/cases
```

A completion claim cites a command and its exit code (`receipts.py`); the
receipts E2E in `tests/test_receipts_e2e.py` proves the loop, and the
quality pack refuses self-approval.
