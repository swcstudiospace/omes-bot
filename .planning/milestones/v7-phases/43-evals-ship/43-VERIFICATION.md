# Verification: Phase 43 Evals + ship

**Status:** passed
**Date:** 2026-10-03

## Success criteria

1. Opt-in read-only live probes (substrate healthz, hindsight health,
   brief fetch) run manually against Railway with no secrets printed and
   no CI dependency — PASS (probe module + read-only/secret-free tests +
   manual run above; local 503 reported truthfully, reads green).
2. Substrate eval cases pass, setup_check covers the surface env, the Grok
   Bot template/routines name the surface, and a GitBook docs page
   describes it — PASS (23/23 evals; substrate setup check; template
   Description + SETUP rows; `docs/substrate.md` in SUMMARY).

## Commands

- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 294 passed.
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 23 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omega_prime.setup_check --root .` → exit 0.
- `.venv/bin/python -m omega_prime.substrate.probes` → exit 1 (degraded local writer, reads ok).

## Requirements

- PRB-01: Done. SHP-01: Done.
