# Roadmap: Omega Prime

## Milestones

- ✅ **v1 One Omega Prime agent** — Phases 1-12 (shipped 2026-10-03)
- ✅ **v2 Enterprise hardening** — Phases 13-16 (shipped 2026-10-03)
- ✅ **v3 Grok Bot** — Phases 17-20 (shipped 2026-10-03)
- ✅ **v4 Third-party integrations** — Phases 21-25 (shipped 2026-10-03)
- ✅ **v5 Desk packs** — Phases 26-33 (shipped 2026-10-03)
- ✅ **v6 Grok ship** — Phases 34-38 (shipped 2026-10-03)
- ✅ **v7 Substrate surface** — Phases 39-43 (shipped 2026-10-03)
- ✅ **v8 Public launch** — Phases 44-45 (shipped 2026-10-03)
- ✅ **v9 SOTA upgrade** — Phases 46-52 (shipped 2026-10-08)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v9-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v9-phases/`.

## v9 Overview

v8 launched the repo in public (see `milestones/v8-ROADMAP.md`). v9
brings the same one-agent product to state-of-the-art standards: the
in-flight hardening in the tree lands verified, lint + types run in CI,
dependencies pin with a lockfile, providers gain retries/usage/Responses/
streaming, red-teaming grows orchestrator + scorer depth, and evals + docs
stay current. Numbering continues. A phase is done when its success
criteria pass; verification stays hermetic (live probes manual opt-in).

## Phases

- [x] **Phase 46: Land in-flight hardening** - Waves 1-3 complete (SEC-NET 2.2.0 egress transport, sandbox boundary, composition, and documentation).
- [x] **Phase 47: Lint + format + types** - Ruff + checker, zero errors, in CI. (completed 2026-10-07)
- [x] **Phase 48: Dependencies + matrix** - Implementation and interpreter verification complete (3.12-3.14 verified). (completed 2026-10-07)
- [x] **Phase 49: Provider resilience** - Retries, usage, current defaults. (completed 2026-10-07)
- [x] **Phase 50: Provider protocols** - Responses mode, streaming. (completed 2026-10-07)
- [x] **Phase 51: Red-team depth** - Hermetic isolation, orchestrators, scorers. (completed 2026-10-07)
- [x] **Phase 52: Answers + evals + docs** - Chunks, eval growth, docs refresh. (completed 2026-10-07)

## Phase Details

### Phase 46: Land in-flight hardening

**Goal**: The 24 uncommitted files land verified; the tree is clean.
**Depends on**: v8 complete
**Requirements**: LAND-01, LAND-02
**Success Criteria** (what must be TRUE):

  1. `pytest omega_prime/tests -q` passes with the landed changes (no new skips).
  2. `omega_prime.evals.runner` passes and `assemble-prompts.sh --check` passes.
  3. Roster/policy/template composition tests cover every touched name.
  4. Working tree contains no uncommitted v9-previous edits.

Plans:

- [x] 46-01: Verify and land the in-flight hardening
- [x] 46-02: Safe destination transport and fetch gap closure
- [x] 46-03: Mandatory browser egress and lifecycle enforcement
- [x] 46-04: Registry, browser, and policy composition
- [x] 46-05: Receipt-sourced security and operator documentation

**Continuation audit (2026-10-07):** Original plan/landing evidence is preserved.
The retroactive enforcing security gate found two high SSRF control gaps.
LAND-01 remains partial. The user chose remediation, not risk acceptance.
SEC-NET 1.1.0 was rejected; revise the focused gap plans before execution.
Native GSD agents are authorized for continuation; v9 archival stays blocked
until real security, runtime, and matching-head CI evidence passes.

### Phase 47: Lint + format + types

**Goal**: Lint, format, and types are clean and CI-enforced.
**Depends on**: Phase 46
**Requirements**: HYG-01, HYG-02, HYG-03
**Success Criteria** (what must be TRUE):

  1. `ruff check` passes on the repo and runs in CI (ruff pinned in dev extra).
  2. `ruff format --check` passes on the repo and runs in CI.
  3. The typechecker reports zero errors on `omega_prime/` and runs in CI via pip only.
  4. Suite + evals + assemble stay green after all lint/type fixes.

Plans:

- [x] 47-01: Ruff + mypy clean and CI-enforced

### Phase 48: Dependencies + matrix

**Goal**: Reproducible installs on every supported Python.
**Depends on**: Phase 47
**Requirements**: HYG-04, HYG-05, HYG-06
**Success Criteria** (what must be TRUE):

  1. Dependency floors are raised to verified versions with a committed lockfile.
  2. CI matrix runs the suite on 3.12, 3.13, and 3.14 (floor stays 3.11).
  3. `import omega_prime.tools.discord` and the suite pass on 3.13+ (audioop-safe).
  4. `mcp>=2,<3` is pinned with no v1-isms and conformance recorded.

Plans:

- [x] 48-01: Floors, lockfile, matrix, discord guard, MCP pin
- [x] 48-02: CI receipts, real interpreter matrix, and matching-head hosted evidence

### Phase 49: Provider resilience

**Goal**: Provider calls survive transients and report usage.
**Depends on**: Phase 48
**Requirements**: PCUR-01, PCUR-02, PCUR-05
**Success Criteria** (what must be TRUE):

  1. Transient provider failures retry with backoff behind FakeTransport tests.
  2. Per-turn token usage is recorded and asserted in provider tests.
  3. Anthropic default max_tokens is raised and model defaults are current.
  4. Suite + evals stay green; no live calls in committed tests.

Plans:

- [x] 49-01: Retry 408/429, usage accounting, current defaults

### Phase 50: Provider protocols

**Goal**: Modern OpenAI protocol plus streamed turns.
**Depends on**: Phase 49
**Requirements**: PCUR-03, PCUR-04
**Success Criteria** (what must be TRUE):

  1. OpenAI provider speaks Responses on api.openai.com with chat_completions fallback.
  2. xAI/compatible endpoints stay on chat_completions (tests pin the routing).
  3. The loop consumes streamed output end to end behind a streaming fake.
  4. Suite + evals stay green; no live calls in committed tests.

Plans:

- [x] 50-01: Responses mode + streaming

### Phase 51: Red-team depth

**Goal**: Hermetic suite plus orchestrator/scorer red-teaming.
**Depends on**: Phase 50
**Requirements**: DPT-01, DPT-02, DPT-03
**Success Criteria** (what must be TRUE):

  1. No test writes outside the repo/tmp; suite collects clean in sandboxes.
  2. PyRIT orchestrator-driven multi-turn attacks run, keyless subset in CI.
  3. Scorer-based judging runs on adversarial evals, keyless subset in CI.
  4. Suite + evals stay green; PyRIT memory stays in-memory/file-isolated.

Plans:

- [x] 51-01: Isolation + orchestrator campaigns + scorer judging

### Phase 52: Answers + evals + docs

**Goal**: Better answers, deeper evals, truthful docs.
**Depends on**: Phase 51
**Requirements**: DPT-04, EVAL-01, EVAL-02
**Success Criteria** (what must be TRUE):

  1. docs_search returns extracted chunks (tests pin shape over raw payload).
  2. New golden + red-team cases cover v9 refusal/contract behavior, all passing.
  3. Setup, model defaults, and tool catalog read true against v9 code.
  4. Full gates green: suite, evals, assemble, lint, types, catalog --check.

Plans:

- [x] 52-01: Chunked answers + eval growth + truthful docs
