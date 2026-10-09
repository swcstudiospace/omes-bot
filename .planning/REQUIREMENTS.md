# Requirements: Omega Prime v12 Programming Desk merge

**Defined:** 2026-10-09
**Core Value:** One Omega Prime (`bot-00-omega-prime`) runs the seven-seat Programming Desk
natively — desk tools configured and live, the agent programming a target repo, subbots via
`delegate_task`, receipts machine-checked, gates targeting the work repo — all served through
the Grok Bot host, so a fresh clone runs the scripts and the backend through Grok Bot properly.

Source: `/root/src/repos/programming-desk` (seven-seat desk OS: LEAD + five build seats +
QUALITY off-channel; verification receipts; path ownership; executable quality gates;
contract-first cross-bot protocol) pinned at `9de3aa3`. Merge direction per user instruction
(2026-10-09): behavior-port the design pattern **under Omega Prime — a single bot controlling
subbots** — not a second gateway deployment. The v5 surface port (49/50 desk tools, 24 skills)
is real but unconfigured: every SEED-005 gap was re-verified on the current tree
(8/8 CONFIRMED-GAP; scout report archived in this phase's CONTEXT). Dormant seeds activated:
SEED-005, SEED-014 (real end-to-end verification evidence). The v11 requirements are archived
in `milestones/v11-REQUIREMENTS.md`.

## v12 Requirements

### Desk runtime activation (Phase 64)

- [ ] **DESK-01**: Desk contexts are configured at host build. `LeadContext` receives a shared
  `MemoryStore`, live `IntakeStore`/`RosterStore`/`EventStore` under `OMEGA_PRIME_STATE_DIR`,
  the `SubstrateClient` and the registry; `lead_doctor` reports green on memory, tools and
  substrate on a real process (no credential required), and `lead_brief`, `lead_intake_next`,
  `lead_memory_retain/recall`, `lead_event_emit` return real results, not `not_configured`.
- [ ] **DESK-02**: Install root and work root are separate. A work root (`--work-root` /
  `OMEGA_PRIME_WORK_ROOT`, default = install root) drives the coding/file/terminal tools, the
  IDE/LSP/DAP jail and `QualityContext.root`, while roster/policy/contract/prompt/ownership
  lookups stay at the install root. Proven by a test that edits, searches and lint-checks a
  file in a foreign repo tree and refuses escapes outside the work root.
- [ ] **DESK-03**: `delegate_task` is served. The host (MCP stdio session and Grok Bot host)
  gets a parent/session handle and registers the delegate tool; the served list includes it
  (manifest, `/healthz` tool count and `catalog --check` agree); a delegated child turn runs
  in-process and returns a result.
- [ ] **DESK-04**: The lead pass runs in production. One dispatch closure (ticket →
  delegate/subagent → receipt dict) is wired to `run_lead_pass` and reachable from a real
  entry point (cron job or heartbeat tick), sharing the same `IntakeStore` as the lead tools;
  an end-to-end intake → claim → ticket → dispatch → receipt → ack flow passes on real stores.
- [ ] **DESK-08**: Desk configuration surface. `OMEGA_PRIME_DESK_*` env (bus URL, notifier,
  docs index, work root) flows into the desk contexts through the same pattern as the existing
  provider env wiring; unconfigured optional surfaces degrade loudly, never silently.

### Receipts, gates and service clients (Phase 65)

- [ ] **DESK-05**: Gates run against the work repo. `qua_gates_run` accepts a target (work
  root or explicit repo path) and a suite selection seam; hardcoded `omega_prime/*` argv is
  replaced by per-repo suite discovery/config; running gates on a target repo executes that
  repo's suites and reports their real exit codes.
- [ ] **DESK-06**: Receipts are machine-checked and approvable. Command executions are captured
  into an auditable store; `validate_receipt` verifies cited commands and exit codes against
  the captured executions (not model-typed text); a second approving identity exists (operator
  approval path), so a `bot-00-omega-prime` receipt can be approved without self-approval.
- [ ] **DESK-07**: Real service clients behind credentials. Railway, Greptile, Vercel, a wired
  browser factory (Playwright via `GuardedBrowserFactory`) and Play Console/App Store Connect
  clients follow the existing env-token wiring and credential-broker provider shape; each is
  exercised live only when credentials exist, and otherwise reports honest `not_configured`.
  Per recorded decisions (2026-10-07): substrate mediation stays; Tailscale forwarders are the
  default network path; no Railway resource changes.

### Grok Bot clone-and-run proof (Phase 66)

- [ ] **DESK-09**: The host reports the desk truthfully. Manifest capabilities, `/healthz`
  tool count, `verify` and the served roster reflect the desk-activated tool set;
  `absorbed_seats` metadata is consumed by code or removed; the Grok Bot template's
  "paused until lead_doctor is green" gate now passes on a launched host.
- [ ] **DESK-10**: A fresh clone runs the backend through Grok Bot. The documented
  clone → install → self-checks (`setup_check`, `catalog --check`, `assemble --check`) →
  attach sequence is executed for real in this milestone's verification, over a real
  transport, including a desk tool call; README/docs carry the verified checklist.
- [ ] **DESK-11**: Three-source port evidence is current. A verification pass cites where
  Hermes, Omp and Prime logic live and re-runs their proof points (loop probe, roster/policy
  parity, Prime family flags) on the final tree, with the prime-agent submodule pin recorded.

### Milestone audit + closeout (Phase 67)

- [ ] **DONE-01**: The v12 audit cites a passing command + exit code for every requirement.
- [ ] **DONE-02**: ROADMAP/MILESTONES/STATE reflect v12 complete; phase dirs archived to
  `milestones/v12-phases/`; full gate suite green on the final tree.

## Acceptance gates (every phase)

Full pytest suite, evals runner, `assemble-prompts.sh --check`, `catalog --check`,
`setup_check`, `ruff check` + `ruff format --check`, `mypy omega_prime/`, and (changed files)
pyright — before a phase is verified. Real-process evidence over fake-only proofs for every
DESK requirement (SEED-014).
