# Phase 66 Plan: Grok Bot clone-and-run proof

**Requirements:** DESK-09, DESK-10, DESK-11. Depends on Phase 65.

## DESK-09 truthful host

- Manifest tool count, `/healthz`, `setup_check`, and the served roster all report the same count (109 plus any Phase 65 tools; do not hardcode).
- `omega_prime/grokbot/templates/OMEGA_PRIME.md` desk-lead line: it stays paused only for the checks that are still red (prompt install / seat register). State which checks are green out of the box (memory, tools, substrate).
- Docs that still say delegate_task is not served, or that the host serves 108 tools, get corrected to the live behavior: `docs/agent-loop.md`, `docs/driving-the-bot.md`, `docs/grok-bot-native.md`, `docs/tool-host.md`, `README.md`.
- `grokbot/rosters/default.json` `absorbed_seats` is read by the lead roster status (or deleted if nothing consumes it). Prefer reading it: `lead_roster_status` reports the seven absorbed seats from that file.

## DESK-10 fresh clone

Document and execute, in verification, this sequence from a clean checkout of this branch:

1. `python -m venv .venv && .venv/bin/pip install -r requirements-lock.txt`
2. `git submodule update --init --recursive` (prime-agent)
3. `python -m omega_prime.setup_check --root .`
4. `python -m omega_prime.tooling.catalog --check`
5. `bash omega_prime/scripts/assemble-prompts.sh --check`
6. `python -m omega_prime.grokbot.oneclick --dry-run` (exit 0) and a loopback `--self-test` or an equivalent real-socket MCP client that lists tools and calls one desk tool (`lead_doctor` or `lead_brief`).

README quickstart gains the work-root flag and the desk env vars. Every command in the new section is one that verification actually ran.

## DESK-11 three-source evidence

A short `66-PORT-EVIDENCE.md` cites, with file paths, where Hermes (`omega_prime/agent/`), Omp (roster, policy, registry), and Prime (`omega_prime/prime/`, `prime_kernel/`, tools rlm/goals/heartbeat/autonomous/agent_message, `VENDOR.md`, `contracts/prime-agent.pin.json`) live, and re-runs: setup_check, one Prime-flag-off roster assertion (delegate served, prime families absent by default), and the existing prime loop test module if it stays green in the phase suite.

## Verification

Full pytest, mypy, ruff, evals, assemble, catalog, setup_check, plus the real-socket desk call. Record exit codes in `66-VERIFICATION.md`.
