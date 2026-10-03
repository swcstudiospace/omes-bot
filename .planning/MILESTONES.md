# Milestones

## v8 — Public launch (2026-10-03)

**Status:** Complete. 2/2 phases, 2/2 plans, 7/7 requirements Done.

**Core value delivered:** The repo launched in public — branded README with
icon/banner art, full community files, richer GitBook docs with a generated
tool catalog kept fresh by CI, Greptile review standards in-repo, and a KB
sync pipeline (script + scheduled workflow) publishing Greptile's knowledge
base into `kb/`.

**Verification:** `.venv/bin/python -m pytest omes/tests -q` → exit 0, 310 passed. `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 23 passed. `assemble-prompts.sh --check` → exit 0. `omes.setup_check` → exit 0. Workflows parse; catalog `--check` green.

**Archive:** `milestones/v8-ROADMAP.md`, `milestones/v8-REQUIREMENTS.md`, `milestones/v8-MILESTONE-AUDIT.md`, `milestones/v8-phases/`.

**Decisions:** connect Greptile now (blocked on org app install — user step); push branch + open PR; GitBook stays the host with verify-only CI.

**Deferred:** Pages deploy, per-module API reference, live KB content, PR merge (user).

**Tech debt / known limits:** prose counts refresh by hand; CODEOWNERS/FUNDING.yml skipped (no confirmed handle/sponsor); KB enrollment needs Greptile contact + org key.

## v7 — Substrate surface (2026-10-03)

**Status:** Complete. 5/5 phases, 5/5 plans, 10/10 requirements Done.

**Core value delivered:** Omes Bot as a first-class substrate surface — a fail-open substrate-mcp client (brief/events/shared memory/docs/graph), episodic retain/recall/reflect on the shared `ultrathink` Hindsight bank with local fallback, brief-on-open + turn/tool/file trail with graph provenance in the loop, five rostered substrate tools with approval-gated graph mutations, and a test-enforced ban on direct GreptimeDB/TimescaleDB/DragonflyDB clients.

**Verification:** `.venv/bin/python -m pytest omes/tests -q` → exit 0, 294 passed. `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 23 passed. `assemble-prompts.sh --check` → exit 0. `omes.setup_check` → exit 0. Live probes + audit E2E prove fail-open against the real (degraded) local substrate.

**Archive:** `milestones/v7-ROADMAP.md`, `milestones/v7-REQUIREMENTS.md`, `milestones/v7-MILESTONE-AUDIT.md`, `milestones/v7-phases/`.

**Decisions:** substrate-mediated direction (store lock enforced by test); shared `ultrathink` bank; fakes + opt-in read-only live probes, never in CI.

**Deferred:** signed handoff packets, lease steal/drift, A2A teachables, OTLP (upstream phases); live Hindsight round trip (needs API key).

**Tech debt / known limits:** docs_search returns the raw retrieval payload (no chunk extraction yet); local substrate degraded here so live emit/search degrade; Add-Bot template runs unwired by design (localhost unreachable from xAI).

## v6 — Grok ship (2026-10-03)

**Status:** Complete. 5/5 phases, 5/5 plans, 11/11 requirements Done.

**Core value delivered:** Omes as a Grok Bot Add-Bot product — Omp magic keywords in the loop (differential-clean vs Omp), ultrathink natively integrated (skill + turn routine + 7 CLI bridge tools, zero AGPL vendored), the registry served over MCP stdio with OpenShell/AgentOS host profiles, a polished template + four-step setup flow with a runnable smoke check, MIT license, and a six-page docs set structured for GitBook Git Sync.

**Verification:** `.venv/bin/python -m pytest omes/tests -q` → exit 0, 235 passed. `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed. `assemble-prompts.sh --check` → exit 0. `omes.setup_check` → exit 0.

**Archive:** `milestones/v6-ROADMAP.md`, `milestones/v6-REQUIREMENTS.md`, `milestones/v6-MILESTONE-AUDIT.md`, `milestones/v6-phases/`.

**Decisions:** hybrid runtime (template + optional MCP tool host) from the runtime spike; MIT license with bridge-only ultrathink integration; docs verified claim-by-claim against the codebase.

**Deferred:** Grok marketplace listing (staff-added, no self-serve); GitBook/GitHub Sync connection (dashboard action); Greptile connection for the new repo (dashboard action).

**Tech debt / known limits:** ultrathink max-effort override not ported (no Omes knob); workflowz eval-kernel contract rewritten for delegate batches; delegate excluded from the MCP server (needs a live parent); AgentOS cannot host CPython (actor-calls-host pattern documented).

## v5 — Desk packs (2026-10-03)

**Status:** Complete. 8/8 phases, 9/9 plans, 21/21 requirements Done.

**Core value delivered:** the entire Programming Desk absorbed into Omes as Lead with domain packs — intake/dispatch/consolidate routines plus core/lead tools, systems/web/mobile/infra/quality tool families with platform skills, a real Playwright browser transport and Appium/adb/simctl device seams behind vision review, the 9 app-pack tools with pack load/unload and the 20-tool ceiling, all 24 desk skills, and the seat prompts/templates/roster/ownership/contract versions merged into Omes contracts, guarded by per-pack evals and a receipts E2E.

**Verification:** `.venv/bin/python -m pytest omes/tests -q` → exit 0, 219 passed. `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 21 passed. `assemble-prompts.sh --check` → exit 0.

**Archive:** `milestones/v5-ROADMAP.md`, `milestones/v5-REQUIREMENTS.md`.

**Decisions:** one Omes Lead with packs over a 7-seat port, entire-desk scope, interactive device review (user chose all three); sync clients with injected seams and fakes only in tests; Omes `{"error": "code: reason"}` shape; approval on desk write kinds; template Enabled-skills/Routines sections stay empty per contract; pack evals assert approval/policy machinery while pack logic stays in unit tests; receipts E2E runs hermetic local commands only.

**Deferred:** live browser/device runs (Playwright/Appium seams exist, tests use fakes); YAML contract-ack consumers (no YAML parser — JSON only); desk changes/events contracts (outside REM-03 scope).

**Tech debt / known limits:** no live-endpoint verification (fake transports/peers + scripted servers only, as in v1–v4); pack eval cases stub the tools so they assert machinery, not pack logic; ownership merge keeps the single Omes owner with desk patterns recorded.

## v4 — Third-party integrations (2026-10-03)

**Status:** Complete. 5/5 phases, 5/5 plans, 11/11 requirements Done.

**Core value delivered:** the Grok Bot wired to third-party libraries as real pip dependencies — a tweepy X transport behind the existing connector, an official-SDK MCP session client beside the one-shot caller, a PyRIT target with a keyless adversarial battery, an APScheduler backend driving JobStore jobs, and Telegram + Discord connector families in the Phase 17 shape with roster and policy entries.

**Verification:** `.venv/bin/python -m pytest omes/tests -q` → exit 0, 167 passed. `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed. `assemble-prompts.sh --check` → exit 0.

**Archive:** `milestones/v4-ROADMAP.md`, `milestones/v4-REQUIREMENTS.md`.

**Decisions:** pip deps over in-house ports for all six libraries (user chose all-candidates + pip deps); tweepy transport is bearer-only with an injectable client factory; media upload stays raw HTTP behind a fallback; PyRIT memory is in-memory SQLite; scheduler entries are memory-only with the JSON store authoritative and fires serialized; Discord is REST-only with no gateway.

**Deferred:** OAuth1 user-context for live posting; chunked media upload; PyRIT orchestrator-driven multi-turn attacks and scorer-based judging; sweep/nightly wiring to the scheduler service; live inbound listeners for Telegram/Discord.

**Tech debt / known limits:** no live-endpoint verification (fake transports/peers + scripted servers only); discord.py pulls an `audioop` deprecation warning on 3.12; CI install time grows with the six dependencies.

## v3 — Grok Bot (2026-10-03)

**Status:** Complete. 4/4 phases, 4/4 plans, 10/10 requirements Done.

**Core value delivered:** the hardened agent as a working Grok Bot — an X connector family (mentions, posts, threads, media) with approval-gated publishing and brokered credentials, an engagement sweep producing queued drafts with per-mention checkpoints, nightly learning through the curator, and a deterministic eval harness (golden + red-team) with CI.

**Verification:** `python3 -m pytest omes/tests -q` → exit 0, 126 passed. `python3 -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed. `assemble-prompts.sh --check` → exit 0.

**Archive:** `milestones/v3-ROADMAP.md`, `milestones/v3-REQUIREMENTS.md`.

**Decisions:** publishing requires approval, staging does not; sweeps draft but never publish; tool arguments still never logged; CI runs suite + evals + assemble check.

**Deferred:** X search, streaming, likes/follows, chunked upload, OAuth flows; model-judged evals; cron scheduling of sweep/nightly pass.

**Tech debt / known limits:** no live X verification (fake transports only); composer and transcripts are caller-supplied; eval coverage is six cases.

## v2 — Enterprise hardening (2026-10-03)

**Status:** Complete. 4/4 phases, 4/4 plans, 12/12 requirements Done.

**Core value delivered:** the v1 agent, hardened OpenShell/AgentOS-style — a declarative seat policy enforced at dispatch with advisor diffs and a persisted audit log, a credential broker that keeps keys out of transcripts with secret redaction, durable runs (SQLite turn journal, cron history, checkpointed workflows), and a real stdlib HTTP transport with structured trace export. Still one in-process Python agent with one seat.

**Verification:** `python3 -m pytest omes/tests -q` → exit 0, 113 passed. `assemble-prompts.sh --check` → exit 0. v2 stack E2E probe (policy + broker + HTTP + audit + trace + journal in one turn) passes.

**Archive:** `milestones/v2-ROADMAP.md`, `milestones/v2-REQUIREMENTS.md`.

**Decisions:** JSON policy file (stdlib-exact, no YAML parser); tool arguments never logged; shipped network allowlist stays empty (deny by default); socketpair HTTP fixtures (loopback TCP is sandbox-blocked here).

**Deferred:** container/namespace execution drivers; fleet gateway and multi-seat registry; formal policy prover; MCP inspection server.

**Tech debt / known limits:** secret redaction is pattern-based; journal is single-process SQLite; no live-endpoint verification (fake transports + scripted peers only); no streaming, usage accounting, or secret managers beyond the environment.

## v1 — One Omes agent (2026-10-03)

**Status:** Complete. 12/12 phases, 12/12 plans, 49/49 requirements Done.

**Core value delivered:** one Omes agent runs both Hermes and Omp agent logic — loops, subagents, tools, skills, memory, and the rest of each runtime.

**Verification:** `python3 -m pytest omes/tests -q` → exit 0, 94 passed. `bash omes/scripts/assemble-prompts.sh --check` → exit 0. Provider→loop→registry E2E probe passes. No fixture process left running.

**Archive:** `milestones/v1-ROADMAP.md`, `milestones/v1-REQUIREMENTS.md`.

**Decisions:** one Python process with one agent class; Hermes moved and adapted, Omp ported as behavior checked against its TypeScript tests; Temporal deferred to a later durability adapter; product chrome stays out; roster/template match the registry exactly.

**Deferred:** Temporal adapter after cron and delegation; TUI, desktop, gateways, Rust crates, packaging.

**Tech debt / known limits:** recall paths are deterministic substring matches (no embeddings); repair passes are deterministic (no model regeneration); providers tested behind a fake transport only (no live network); learn-memory backend, streaming, retries, OAuth, and usage accounting are out of scope.
