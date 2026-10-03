---
phase: 08-edit-pipeline
plan: 01
subsystem: tools
tags: [edit, patch, repair, fuzzy]
provides:
  - Exact-first edit pipeline with offset and whitespace-fuzzy repair
affects: [09-lsp-and-dap]
---

# Phase 8 summary

`apply_edit` tries the exact unified-diff apply first, then re-anchors hunks with wrong header line numbers by unique context search (`offset`), then matches whitespace-only context differences fuzzily while keeping the file's own context bytes (`fuzzy`). A hunk matching nowhere or in more than one place fails every pass, and a malformed diff fails before any pass; total failure leaves the file byte-for-byte unchanged. `FileWorkspace.edit_file` exposes the pipeline with `patch_file`'s error shapes plus the winning `method`, and `edit_file` is registered after `patch_file` and listed on the roster in that position. `patch_file` stays strict and unchanged.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `67 passed in 3.42s` (`test_edit.py`: 7 passed)

Unverified: model-driven regeneration, tree-sitter parse checks, the Rust `EditSession`, LSP writethrough, and the blackbox recorder.
