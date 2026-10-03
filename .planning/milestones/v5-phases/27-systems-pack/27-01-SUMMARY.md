# Summary 27-01: Systems tools and skills

## What shipped

`omes/tools/systems.py`: 6 registry tools porting desk `systems.py`
(SQL index/events queries, TTL cache, Tier-1 LSP diagnostics through the
Omes session flow, contract proposals as operator-committed bundles with a
hand-emitted changes YAML, main-ref design reads). Approval on `sys_cache`
and `sys_contract_propose`, mirroring desk roster kinds.

`omes/skills/rust/SKILL.md`, `omes/skills/python/SKILL.md`: desk platform
skills with `bots:` repointed to `bot-00-omes` and desk-internal references
adapted (supply-chain ref lands in Phase 31).

Roster, shipped policy, and the three composition assertions extended.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_systems.py -q` → exit 0, 6 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 187 passed (181 + 6).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
