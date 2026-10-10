# Phase 64 Summary: Desk runtime activation

**Requirements:** DESK-01, DESK-02, DESK-03, DESK-04, DESK-08. All wired.

The host now builds the desk with live seams. `default_registry` shares one
`MemoryStore` between the growth tools and the lead pack, and gives the lead
pack an `IntakeStore`, `RosterStore`, and `EventStore` under
`OMEGA_PRIME_STATE_DIR` (else `<work-root>/omega_prime/state`). The same
substrate client the substrate tools use backs `lead_event_emit` and
`lead_doctor`. `lead_doctor` is green on memory, tools, and substrate with no
credentials.

`--work-root` / `OMEGA_PRIME_WORK_ROOT` is the directory the desk works on.
Coding tools, the IDE jail, and `QualityContext.root` follow it. Roster,
policy, prompts, and ownership stay on the install root. The default (work
root = install root) keeps today's `omega_prime/` coding jail.

`delegate_task` is on the served roster (109 tools). The parent is an
in-process shim using the same provider env as the loop. With no provider
env the tool returns `not_configured: provider` and does not invent a child.

`run_lead_pass` has a production dispatch closure (`make_dispatch`) and a
`desk_lead_pass` cron kind. `DeskDriver` ticks due passes on the shared
`cron/jobs.json` store. The live server starts it (`main` for stdio,
`serve_sse` for the Grok Bot host) and stops it on shutdown. Building a
registry for doctor, setup check, or tests does not start the thread.
Scheduler model ticks skip the desk kind, so a desk pass never burns a model
call there. A missing parent blocks the ticket with a real failure receipt.

Optional desk env: `OMEGA_PRIME_DESK_BUS_URL`, `OMEGA_PRIME_DESK_DOCS_INDEX`,
`OMEGA_PRIME_DESK_NOTIFY_URL`. Unset surfaces stay an explicit
`not_configured` result.
