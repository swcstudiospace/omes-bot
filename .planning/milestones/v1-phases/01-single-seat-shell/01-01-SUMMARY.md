---
phase: 01-single-seat-shell
plan: 01
subsystem: prompts
tags: [grokbot, xml, receipts]
provides:
  - Single-seat prompt, assembler, empty roster, and template
affects: [02-hermes-loop]
key-files:
  created:
    - omega_prime/prompts/_shared/core-directives.xml
    - omega_prime/prompts/bot-00-omega-prime.xml
    - omega_prime/prompts-assembled/OMEGA_PRIME.xml
    - omega_prime/assemble.py
    - omega_prime/receipts.py
    - omega_prime/grokbot/templates/OMEGA_PRIME.md
    - omega_prime/contracts/tool-rosters/omega-prime.yaml
---

# Phase 1 summary

The Omega Prime seat prompt points at `skills/`, `contracts/tool-rosters/omega-prime.yaml`, and `prompts/`. Assembling twice yields the same bytes. The template lists no skills and no routines, and the checker rejects a name that is not on disk. PD-1, PD-4, and PD-5 are in the core directives. `validate_receipt` rejects a claim with no command and a destructive operation with no approval.

## Verification

Command: `python3 -m pytest omega_prime/tests/test_shell.py -q`

Exit code: 0

Output tail: `11 passed in 0.09s`

Unverified: a live Grok account was not provisioned. The template file is the install surface.
