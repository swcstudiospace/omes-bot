---
status: complete
requirements_completed: [BND-07, BND-08, BND-09]
---

# Phase 73 Summary: Plane surfaces

**Requirements:** BND-07, BND-08, BND-09. All wired.

Cron admin is `cron_jobs_list`, `cron_job_create`, and `cron_job_remove` in `omega_prime/tools/cron_admin.py`. Each call opens the scheduler's `root/cron/jobs.json` through `JobStore`. Create goes through `schedule_desk_lead_pass`, `schedule_heartbeat`, or `JobStore.schedule`. Create and remove require approval. The scheduler's own tick is unchanged.

Learning is `autolearn_turn`, `advisor_note`, and `advisor_render` in `omega_prime/tools/learning_surface.py`. `autolearn_turn` writes through `Autolearn` and requires approval. The advisor tools render notes and do not call a model. GoalStore is not registered again here. It stays on the goals family, flag `prime.goals.enabled`, store `PrimeGoalStore` at `<root>/goals`, tools `goal_set`, `goal_pause`, `goal_resume`, `goal_clear`, `goal_status`.

Durable: `run_due_jobs` attaches a `TurnJournal` at `cron/turns.sqlite` beside the job store. Construction failure emits `prime_degraded` and the turn still finishes. `attach_journal` wraps the journal so a later write failure emits `prime_degraded` and does not raise. Delegate children share the parent journal when it is a `TurnJournal`. `durable_status` reads `cron/turns.sqlite` and counts `workflows/*.json` checkpoints. A missing journal is `journal: absent`, not an exception.

These seven names are on the roster, the seat policy, and the generated catalog. Default served count is 117. All-flags served count is 154.
