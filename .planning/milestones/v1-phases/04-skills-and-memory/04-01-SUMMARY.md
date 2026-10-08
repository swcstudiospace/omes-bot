---
phase: 04-skills-and-memory
plan: 01
subsystem: agent
tags: [skills, memory, session-search, curator]
provides:
  - Skill manager, memory store, session search, and curator
affects: [05-delegation-and-cron]
---

# Phase 4 summary

`skill_manage` creates, edits, and patches a skill under a caller-supplied root, and `skill_view` loads that file from disk on a later call. Guards refuse a bad name, a path that leaves the root, a broken frontmatter block, and a new description longer than 60 characters. `MemoryStore` writes `MEMORY.md` and `USER.md`. A new store reloads the entry, and `prefetch_all` returns it unless the query is a trivial greeting. `SessionStore` appends messages in sqlite, and `session_search` returns a stored message whose content contains the query. `review_turn` writes a skill through `skill_manage` only when the user asked to save one and a tool result succeeded. Otherwise the skill tree is unchanged.

The roster lists the eleven coding tools, then `skill_manage`, `skill_view`, `memory`, and `session_search`.

## Verification

Command: `python3 -m pytest omega_prime/tests -q`

Exit code: 0

Output tail: `36 passed in 0.23s`

Unverified: no live model. The curator uses the deterministic earn rule, not an LLM review fork. Hermes fuzzy patching and the memory threat scanner were not ported.

## Deferred

- Curator `name:` match is unanchored, so `filename:deploy-check` can count as `name:deploy-check`.
- A failed categorized create can remove an empty category directory that already existed.
- An unreadable memory file clears the in-memory list until a later read succeeds. The file is not overwritten.
- Memory writes truncate in place instead of replacing via a temp file.
- Registry JSON-string passthrough applies to every handler, not only the four growth tools. Coding tools still return dicts and encode once.
