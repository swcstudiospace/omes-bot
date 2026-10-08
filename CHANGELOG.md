# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.html).

## [Unreleased]

### Added

- Pinned development lint/type checks and a Python 3.12–3.14 CI matrix with
  a reproducible dependency lock and an audioop-safe Discord import.
- Provider transient-failure retries, per-turn token usage, OpenAI Responses
  routing with chat-completions fallback, and streamed conversation turns.
- Hermetic PyRIT multi-turn attack campaigns and scorer-based judging.
- SEC-NET 2.2.0 egress transport hardening and verified browser sandbox boundary
  confinement (see [SECURITY.md](SECURITY.md)).

### Changed

- Renamed the product from Omes Bot to Omega Prime: Python package `omes` is
  now `omega_prime`, the distribution is `omega-prime`, the seat is
  `bot-00-omega-prime`, contracts moved to `contracts/tool-rosters/omega-prime.yaml`
  and `contracts/policies/omega-prime.json`, the template is
  `grokbot/templates/OMEGA_PRIME.md`, and `OMES_*` environment variables are
  now `OMEGA_PRIME_*`.
- Documentation search now returns bounded, redacted excerpts and explicit
  citation provenance instead of copying the raw retrieval response.
- Ultrathink mark evals exercise the real approval contract through an injected
  runner; removing the production approval requirement fails the red-team case.
- Setup and tool documentation reflect the 109-tool roster and 108-tool MCP
  surface; test/eval totals are reported by CI instead of pinned in prose.
- Replaced incidental source/configuration-copy assertions with executable
  lint/type/catalog gates and consumer-visible regression coverage.
- CI jobs share a stdlib receipt helper, preserving command failures and
  distinguishing missing, skipped, cancelled, and failed validation evidence.

### Fixed

- Prevented retrieval content, metadata, and error messages from bypassing
  existing credential redaction at registry, MCP, and model boundaries.
- Distinguished malformed docs responses from valid searches with no hits.

## [0.1.0] — 2026-10-03

First public release: one Grok programming bot, eight milestones deep.

### Added

- One-agent runtime (v1): Hermes conversation loop plus the oh-my-pi
  harness — tools, skills, memory, delegation, sessions, modes — in a
  single Python process with a Grok provider and Add-Bot template.
- Enterprise hardening (v2): declarative seat policy, credential broker
  with redaction, durable SQLite runs, stdlib HTTP transport, audit log,
  structured traces.
- Grok Bot flows (v3): X connector with approval-gated publishing,
  engagement sweeps, nightly learning, deterministic eval harness, CI.
- Third-party integrations (v4): tweepy, MCP SDK sessions, PyRIT battery,
  APScheduler backend, Telegram + Discord connectors as real pip deps.
- Desk packs (v5): the Programming Desk absorbed as lead + domain packs —
  systems/web/mobile/infra/quality families, Playwright browser and device
  seams, 24 desk skills, pack evals.
- Grok ship (v6): magic keywords, native ultrathink, MCP tool host,
  template + setup flow, MIT license, GitBook docs.
- Substrate surface (v7): brief-on-open, turn/tool event trail, shared
  memory, Hindsight episodes on the shared bank, RAGflow docs, graph
  coordination, store-lock guard, read-only live probes.
- Public launch (v8): branded README, community files, generated tool
  catalog with CI freshness, Greptile review standards + KB sync pipeline.

[Unreleased]: https://github.com/swcstudiospace/omega-prime/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/swcstudiospace/omega-prime/releases/tag/v0.1.0
