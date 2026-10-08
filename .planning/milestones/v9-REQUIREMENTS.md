# Requirements: Omes Bot v9 SOTA upgrade

**Defined:** 2026-10-07
**Core Value:** One Omes agent runs both agents' logic — v9 brings that same
product to state-of-the-art engineering and agent standards without changing
its one-agent, one-process architecture.

## v9 Requirements

### Land in-flight hardening

- [x] **LAND-01**: In-flight tool hardening (recursive redaction, intake lease
  reclaim/release, write-path hardening) lands with the suite and evals green
  - Continuation audit: Satisfied via SEC-NET 2.2.0 egress transport and browser boundary hardening.
- [x] **LAND-02**: In-flight skill, routine, and doc touch-ups land with
  roster/policy/template composition tests green

### Hygiene

- [x] **HYG-01**: Contributor gets a clean `ruff check` over the repo, enforced
  in CI with ruff pinned exactly in a dev extra
- [x] **HYG-02**: Contributor gets a clean `ruff format --check`, enforced in CI
- [x] **HYG-03**: Contributor gets zero typechecker errors on `omes/`,
  enforced in CI via a pip-installable checker (no Node, no new toolchain)
- [x] **HYG-04**: Contributor installs reproducible floors: dependency minima
  raised to verified versions plus a committed lockfile
- [x] **HYG-05**: Contributor gets a CI matrix covering Python 3.12–3.14
  (floor stays 3.11) with the Discord import guarded for 3.13+
- [x] **HYG-06**: MCP SDK stays on the v2 line (`mcp>=2,<3`) with no v1-isms
  and spec conformance recorded

### Provider currency

- [x] **PCUR-01**: Operator gets transient-failure retries with backoff on
  provider requests
- [x] **PCUR-02**: Operator sees per-turn token usage recorded from providers
- [x] **PCUR-03**: Operator can use the OpenAI Responses API on api.openai.com
  with automatic chat_completions fallback; xAI/compatibles stay on
  chat_completions
- [x] **PCUR-04**: Loop can consume streamed provider output with a hermetic
  streaming fake for tests
- [x] **PCUR-05**: Provider defaults are current: raised Anthropic max_tokens
  and refreshed documented model IDs

### Agent depth

- [x] **DPT-01**: Contributor gets a hermetic suite: no test writes outside the
  repo/tmp (PyRIT home-dir writes isolated; suite collects clean in sandboxes)
- [x] **DPT-02**: Evaluator gets PyRIT orchestrator-driven multi-turn attacks
  with a deterministic keyless subset in CI
- [x] **DPT-03**: Evaluator gets scorer-based judging for adversarial evals
  with a keyless subset in CI
- [x] **DPT-04**: Agent answers docs from extracted chunks instead of the raw
  retrieval payload

### Evals and docs

- [x] **EVAL-01**: Evaluator gets new deterministic cases covering v9 refusal
  and contract behavior (golden + red-team growth)
- [x] **EVAL-02**: Reader gets refreshed docs: setup, model defaults, and tool
  catalog current with v9, counts verified in CI

## v10 Requirements

Deferred to a future milestone. Tracked but not in the v9 roadmap.

### Toolchain

- **TOOLC-01**: Revisit `ty` for typechecking once it reaches 1.0 stable
- **TOOLC-02**: Revisit `uv` for installs/lockfile if the no-new-toolchain
  constraint is lifted by user decision

### Deferred depth

- **DEEP-01**: Signed handoff packets between surfaces
- **DEEP-02**: OTLP trace export (upstream substrate phases)
- **DEEP-03**: Live API verification lanes in CI (needs keys + user decision)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live API calls in committed tests | Hermetic rule since v1; user re-confirmed hermetic + opt-in 2026-10-07 |
| Multi-seat channel mechanics | Out of scope since v1; lead + packs is the architecture |
| Node-based or global toolchains | Repo constraint: one Python process, pip only |
| Grok marketplace listing | Staff-added, no self-serve path (deferred since v6) |
| Product chrome (TUIs, sites, packaging) | Out of scope since v1 |
| Temporal as the merge | Out of scope since v1; one process is the merge |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAND-01 | Phase 46 | Done |
| LAND-02 | Phase 46 | Done |
| HYG-01 | Phase 47 | Done |
| HYG-02 | Phase 47 | Done |
| HYG-03 | Phase 47 | Done |
| HYG-04 | Phase 48 | Done |
| HYG-05 | Phase 48 | Done |
| HYG-06 | Phase 48 | Done |
| PCUR-01 | Phase 49 | Done |
| PCUR-02 | Phase 49 | Done |
| PCUR-05 | Phase 49 | Done |
| PCUR-03 | Phase 50 | Done |
| PCUR-04 | Phase 50 | Done |
| DPT-01 | Phase 51 | Done |
| DPT-02 | Phase 51 | Done |
| DPT-03 | Phase 51 | Done |
| DPT-04 | Phase 52 | Complete |
| EVAL-01 | Phase 52 | Complete |
| EVAL-02 | Phase 52 | Complete |

**Coverage:**

- v9 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-07*
*Last updated: 2026-10-07 after Phase 52 completion and enforcing security/matrix-validation audit*
