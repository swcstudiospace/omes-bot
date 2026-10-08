# Summary 27-01: Systems tools and skills

## What shipped

`omega_prime/tools/systems.py`: 6 registry tools porting desk `systems.py`
(SQL index/events queries, TTL cache, Tier-1 LSP diagnostics through the
Omega Prime session flow, contract proposals as operator-committed bundles with a
hand-emitted changes YAML, main-ref design reads). Approval on `sys_cache`
and `sys_contract_propose`, mirroring desk roster kinds.

`omega_prime/skills/rust/SKILL.md`, `omega_prime/skills/python/SKILL.md`: desk platform
skills with `bots:` repointed to `bot-00-omega-prime` and desk-internal references
adapted (supply-chain ref lands in Phase 31).

Roster, shipped policy, and the three composition assertions extended.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_systems.py -q` → exit 0, 6 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 187 passed (181 + 6).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
