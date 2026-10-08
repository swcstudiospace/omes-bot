# Summary 32-01: Remaining packs, skills, prompts, contracts

## What shipped

`omega_prime/tools/packs.py`: 9 registry tools porting desk `packs.py`
(load/unload with the 20-live-tools ceiling, API smoke with ms
timing, read-only SQL guard + Supabase query, push test, flags,
crashes, scoreboard, store listing, render-job status). Pack table,
API bases, and HTTP client injected; default urllib client; Omega Prime
error shape. Approval on load + push test (desk write kinds).

`omega_prime/contracts/tool-packs/{clippyos,desklanes,kanbanos}.yaml`: desk
pack contracts with consumer repointed to `bot-00-omega-prime`, desk
version 1.0.0 kept.

`omega_prime/skills/`: 11 remaining desk skills
(contract-first-changes, desk-bootstrap, desk-doctor, desk-gateway,
gotxcot-uplift, greptile-merge-gate, hindsight-memory, ragflow-docs,
tool-packs, trackplan-dispatch, verification-receipts), `bots:`
repointed to `[bot-00-omega-prime]` (added where the desk file had none).
All 24 desk skills now present.

REM-03 merges: `<absorbed_seats>` in `bot-00-omega-prime.xml` (7 seats,
remit + owned paths) with `prompts-assembled/OMEGA_PRIME.xml` regenerated;
OMEGA_PRIME.md description records the absorbed seats/skills (Enabled
skills section stays empty per `test_shell.py` contract);
`absorbed_seats` in `default.json`; desk ownership patterns merged
into `omega_prime/ownership.yaml`; absorbed desk contract versions noted in
the roster header. Roster, policy, composition extended.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_packs.py -q` → exit 0, 3 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 217 passed (214 + 3).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 8 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
