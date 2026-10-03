# Milestones

## v1 — One Omes agent (2026-10-03)

**Status:** Complete. 12/12 phases, 12/12 plans, 49/49 requirements Done.

**Core value delivered:** one Omes agent runs both Hermes and Omp agent logic — loops, subagents, tools, skills, memory, and the rest of each runtime.

**Verification:** `python3 -m pytest omes/tests -q` → exit 0, 94 passed. `bash omes/scripts/assemble-prompts.sh --check` → exit 0. Provider→loop→registry E2E probe passes. No fixture process left running.

**Archive:** `milestones/v1-ROADMAP.md`, `milestones/v1-REQUIREMENTS.md`.

**Decisions:** one Python process with one agent class; Hermes moved and adapted, Omp ported as behavior checked against its TypeScript tests; Temporal deferred to a later durability adapter; product chrome stays out; roster/template match the registry exactly.

**Deferred:** Temporal adapter after cron and delegation; TUI, desktop, gateways, Rust crates, packaging.

**Tech debt / known limits:** recall paths are deterministic substring matches (no embeddings); repair passes are deterministic (no model regeneration); providers tested behind a fake transport only (no live network); learn-memory backend, streaming, retries, OAuth, and usage accounting are out of scope.
