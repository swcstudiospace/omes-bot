---
phase: 51-redteam-depth
plan: "01"
subsystem: testing
tags: [pyrit, isolation, redteam]
requirements-completed: [DPT-01, DPT-02, DPT-03]
completed: 2026-10-07
status: complete
---

# Summary 51-01: Isolation + orchestrator campaigns + scorer judging

**Isolated PyRIT writes and added scored multi-turn attack campaigns.**

## What was built

- **DPT-01**: `omega_prime/tests/conftest.py` redirects `XDG_DATA_HOME` into tmp
  before any pyrit import (pyrit mkdirs/touches its data dir at import).
  Suite collects and passes with no `HOME=` workaround; the pre-existing
  Oct 4 `~/.local/share/dbdata/logs.txt` untouched.
- **Target**: multi-turn capability declared; answers the latest turn
  (single-prompt behavior identical; per-turn dispatch in campaigns).
- **DPT-02/03**: `run_campaign(target, objective, turns,
  objective_substring?)` drives `MultiPromptSendingAttack`, pairs turns
  from memory, judges each response with case-sensitive
  `SubStringScorer`s, returns `{objective, outcome, turns, verdict}`
  (missing responses fail; empty campaigns rejected). Optional objective
  scorer wires `AttackScoringConfig`.
- Tests: redirect mechanism + DB path (Linux-gated), empty-campaign
  rejection, state-chaining campaign, cross-turn injection campaign,
  objective outcome SUCCESS/FAILURE. +6 total.

## Verification

Suite → exit 0, 350 passed (344 + 6), no redirect. Evals → 23 passed.
Assemble, ruff, mypy green. Commit `36fd803`.
