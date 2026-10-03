# Milestones

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
