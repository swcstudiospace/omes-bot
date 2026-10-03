# Summary 30-01: Infra tools and skills

## What shipped

`omes/tools/infra.py`: 7 registry tools porting desk `infra.py` (Railway
status/logs/variables/redeploy with production-preferring lookup,
Tailscale tailnet parse + configured forwarder probes, systemd unit states,
data-plane health summary). Desk's hardcoded org forwarder map becomes a
context list (default empty). Approval on redeploy only.

`omes/skills/{railway-tailscale,terraform-k8s,remote-dev-machine}/SKILL.md`:
desk skills with `bots:` repointed. Roster, policy, composition extended.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_infra.py -q` → exit 0, 3 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 203 passed (200 + 3).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
