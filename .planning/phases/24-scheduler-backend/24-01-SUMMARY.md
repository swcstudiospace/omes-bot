# Summary 24-01: APScheduler backend and dependency

## What shipped

`omes/cron/apscheduler_backend.py`: `SchedulerService(store, runner)`
registers one in-memory APScheduler entry per incomplete future job (date
trigger for one-shots, interval trigger for intervals, UTC-aware) and runs
`store.tick` on every fire. `start()` ticks overdue jobs immediately, then
registers entries keyed by job id (double start registers nothing twice);
`stop()` is safe before `start()`. Fires are serialized with a lock because
`tick` claims by exact `now` and concurrent fires interleaved (found by the
shared-due-date test: one job ran twice before the lock).

`pyproject.toml` gains `apscheduler>=3.10` (verified against 3.11.3). CI
already installs the project, so no workflow change.
`omes/cron/scheduler.py` is untouched. This closes the v3-deferred "cron
scheduling of sweep/nightly pass" item at the backend level.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_apscheduler_backend.py -q` →
  exit 0, 6 passed (one-shot persist, interval repeat, shared due date
  exactly-once, restart resume, overdue on start, double-start/stop safety).
  Timing-sensitive tests repeated 3x with no flakes.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 150 passed (144 + 6).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Follow-ups

- Wire the sweep and nightly routines to the service with an agent runner.
- Cron trigger support for calendar schedules (currently date + interval).
