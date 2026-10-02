---
phase: 03-coding-toolset
plan: 01
subsystem: tools
tags: [registry, roster, patch, terminal]
provides:
  - Tool registry and the local coding toolset
affects: [04-skills-and-memory]
---

# Phase 3 summary

One registry dispatches `read_file`, `write_file`, `patch_file`, `search_text`, `run_terminal`, `todo_write`, `todo_read`, `clarify`, `web_search`, `web_extract`, and `vision_analyze`. Paths stay inside a root. The terminal runs an argv list, not a shell string. Web and vision use an injected transport. The roster lists those eleven names, and a registered tool that is not on the roster is not offered. A unified-diff file header is counted only outside hunk bodies, so a deleted line that starts with `-- ` still applies.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `29 passed in 0.14s`

Unverified: no live web or vision provider. Tests inject the transport.
