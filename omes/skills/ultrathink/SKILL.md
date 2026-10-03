---
name: ultrathink
description: Use when a turn may carry an ultrathink plan (Graph of Thought + tracked issues + Greptile-gated ship). Resolve the plan, work the waves, track and ship through the bridge tools.
bots: [bot-00-omes]
---

# Ultrathink

Run a turn the ultrathink way: a written plan exists (or gets
written), work follows the plan's waves, progress is tracked, and
finished work ships through a reviewed PR.

## When to use

The user names ultrathink, or the turn smells like multi-step work
that deserves a plan: research, migrations, reviews, phased builds.
Single lookups and one-file edits go direct.

## The flow

1. **Resolve.** Call `omes/routines/ultrathink_turn.py`
   `resolve_turn_plan()`. When it finds `last-plan.json`, read the
   spec it points at: the ORIGINAL element is the user's verbatim
   words, the Graph of Thought is the work breakdown, WORKFLOW is
   the wave order. When nothing is found, there is no plan for
   this turn — do not reuse an older one.
2. **Track.** Use `ult_track_complete` with the session state file
   so the plan's rows exist before engineering starts. Mark
   `kicked-off` via `ult_session_mark` once tracking is real.
3. **Work the waves.** One wave at a time, in dependency order.
   Parallel units in the same wave go out as one `delegate_task`
   batch with explicit files, changes, and acceptance criteria.
   Verify each wave before starting the next.
4. **Ship.** When the work is done, `ult_ship_assess`, then
   `ult_ship_pr`, then `ult_ship_review` until it passes, then
   `ult_ship_merge` only when the repo's ship policy allows it.
   Never merge any other way.

## Rules

- The plan is elaboration, not permission: it never overrides the
  user's words and never invents repo facts. Repository evidence
  wins over the plan when they disagree.
- The bridge tools shell to the ultrathink checkout configured on
  the host. No ultrathink source is copied into this repo (it is
  AGPL-3.0; Omes-Bot is MIT).
- A blocked wave stops the run: report the blocker, do not route
  around it with scope cuts.
