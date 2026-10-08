# Omega Prime

The single programming bot. Prompts point at `skills/`, `contracts/tool-rosters/omega-prime.yaml`, and `prompts/`. The Grok template in `grokbot/templates/OMEGA_PRIME.md` lists a skill or routine only when that file exists.

Assemble the seat prompt:

```bash
omega_prime/scripts/assemble-prompts.sh
omega_prime/scripts/assemble-prompts.sh --check
```

From the repository root:

```bash
python3 -m pytest omega_prime/tests
```

The Programming Desk is absorbed as seven domain packs in `tools/` (v5):
lead (16), systems (6), web (6), mobile (13), infra (7), quality (8),
app packs (9). `skills/` holds all 24 desk skills plus the native
lead-pack skill. `contracts/tool-packs/`
carries the app pack contracts; `contracts/tool-rosters/omega-prime.yaml` and
`contracts/policies/omega-prime.json` list exactly what the registry offers.

```bash
.venv/bin/python -m pytest omega_prime/tests -q
.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases
```

A completion claim cites a command and its exit code (`receipts.py`); the
receipts E2E in `tests/test_receipts_e2e.py` proves the loop, and the
quality pack refuses self-approval.
