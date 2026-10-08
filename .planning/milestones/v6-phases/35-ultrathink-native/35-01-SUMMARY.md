# Summary 35-01: Ultrathink skills, routines, bridge tools

## What shipped

`omega_prime/skills/ultrathink/SKILL.md` (new, Omega-Prime-authored): the
plan → track → wave → ship flow naming the bridge tools and the
no-vendoring rule. `omega_prime/routines/ultrathink_turn.py` (new):
`resolve_turn_plan` probes `last-plan.json` across the host state
dirs and reports plan/spec paths; missing/unreadable is `found:
False`, never an exception.

`omega_prime/tools/ultrathink.py` (new): 7 bridge tools over the host
ultrathink checkout (`ult_status`, `ult_track_complete`,
`ult_session_mark`, `ult_ship_assess/pr/review/merge`) behind an
injected runner; unconfigured root, non-zero exits, and non-JSON
output handled; approval on track + the three ship writes.
Roster, policy, composition extended. No AGPL source copied.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_ultrathink.py -q` → exit 0, 3 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 227 passed (224 + 3).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
