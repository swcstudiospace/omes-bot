# Contributing to Omega Prime

Thanks for improving the bot. Every change — code, prompts, skills, docs —
passes the same four gates before it merges.

## Setup

```bash
git clone https://github.com/swcstudiospace/omega-prime.git
cd omega-prime
python -m venv .venv && .venv/bin/pip install -e .
```

Python 3.11 or newer. No Node, Rust, or other toolchain: the agent is one
Python process.

## The four gates

Run all four; a PR that skips one does not merge.

```bash
.venv/bin/python -m pytest omega_prime/tests -q
.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases
bash omega_prime/scripts/assemble-prompts.sh --check
.venv/bin/python -m omega_prime.setup_check --root .
```

CI runs the same commands on every push and pull request.

## Working agreements

- **Receipts, not claims.** A completion claim cites the command and its exit
  code. Tests prove behavior; prose describes it.
- **The roster is the truth.** Tools listed in
  `omega_prime/contracts/tool-rosters/omega-prime.yaml` must be exactly the tools the
  registry serves, and the seat policy must allow every one. The suite
  enforces both — update all three together.
- **Hermetic tests.** No network in tests: fakes and scripted peers only.
  Live services are probed by hand (`omega_prime.substrate.probes`), never in CI.
- **No secrets, ever.** Keys resolve through the credential broker from the
  environment. Never commit, print, or paste one — see SECURITY.md.
- **Read-only sources.** `hermes-agent/`, `oh-my-pi/`, and the repos named in
  VENDOR.md are porting references. Port behavior; never vendor, subtree, or
  runtime-import them.
- **Docs stay linked.** Every `docs/*.md` page is listed exactly once in
  `docs/SUMMARY.md` and starts with a top-level heading. Generated pages
  (tool catalog) are rebuilt by script, never hand-edited.

## Pull requests

- One concern per PR, with a summary of behavior change + verification.
- New tools, skills, and routines arrive with tests and roster/policy/docs
  updates in the same PR.
- Fill in the PR template checklist; request review when all four gates
  are green on your branch.

## Milestones

Large work is tracked in `.planning/` (requirements, roadmap, per-phase
plans and verifications). Small fixes don't need planning artifacts —
just the gates above.
