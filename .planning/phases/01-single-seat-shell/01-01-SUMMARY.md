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
    - omes/prompts/_shared/core-directives.xml
    - omes/prompts/bot-00-omes.xml
    - omes/prompts-assembled/OMES.xml
    - omes/assemble.py
    - omes/receipts.py
    - omes/grokbot/templates/OMES.md
    - omes/contracts/tool-rosters/omes.yaml
---

# Phase 1 summary

The Omes seat prompt points at `skills/`, `contracts/tool-rosters/omes.yaml`, and `prompts/`. Assembling twice yields the same bytes. The template lists no skills and no routines, and the checker rejects a name that is not on disk. PD-1, PD-4, and PD-5 are in the core directives. `validate_receipt` rejects a claim with no command and a destructive operation with no approval.

## Verification

Command: `python3 -m pytest omes/tests/test_shell.py -q`

Exit code: 0

Output tail: `11 passed in 0.09s`

Unverified: a live Grok account was not provisioned. The template file is the install surface.
