# Requirements: v5 Desk packs

Milestone-scoped. v4 requirements are archived in `milestones/v4-REQUIREMENTS.md`.
Ground truth: `.planning/codebase/`. User decisions (2026-10-03): Omega Prime stays
one agent (Lead) with domain packs; entire desk scope; interactive device review.

## Lead pack

- [x] **LEAD-01**: Intake→ticket→dispatch→consolidate→report runs as Omega Prime routines on delegate/todo/registry/approval machinery.
- [x] **LEAD-02**: Desk core+lead tools ported as registry families (brief, ownership, events, doctor, intake, graph, bus, roster, prompt render).
- [x] **LEAD-03**: Desk memory/retention and receipt-check map onto Omega Prime memory and receipts without duplication.

## Systems pack

- [x] **SYS-01**: Systems tools ported (index/events query, cache, contracts, design artifacts; LSP wired to the existing Omega Prime LSP).
- [x] **SYS-02**: Rust + Python platform skills land in `omega_prime/skills/`.

## Web pack

- [x] **WEB-01**: Web tools ported (Vercel lifecycle, preview_check, bundle secret scan).
- [x] **WEB-02**: Real browser transport (Playwright) behind `BrowserSession`; screenshots flow into `vision_analyze` with connectivity checks.
- [x] **WEB-03**: TypeScript/Deno + Vercel platform skills land in `omega_prime/skills/`.

## Mobile pack

- [x] **MOB-01**: Store tools ported (Play tracks/rollouts, TestFlight, phased releases, size/lint/entitlements gates, review risk).
- [x] **MOB-02**: Interactive device transports (Appium/adb/simctl) with screenshot review wired to vision; no live devices in tests.
- [x] **MOB-03**: Android + iOS platform skills land in `omega_prime/skills/`.

## Infra pack

- [x] **INF-01**: Infra tools ported (Railway lifecycle, Tailscale, VPS units, DB health).
- [x] **INF-02**: Railway/Tailscale, Terraform/K8s, remote-dev-machine skills land in `omega_prime/skills/`.

## Quality pack

- [x] **QUA-01**: Quality tools ported (gates_run, greptile_review, receipt_approve, waivers, contract ack, supply-chain, secret scan).
- [x] **QUA-02**: Desk CI gates mirrored as Omega Prime eval cases + CI checks.
- [x] **QUA-03**: Code-review, debugging, security skills land in `omega_prime/skills/`.

## Packs + skills remainder

- [x] **REM-01**: App tool-pack tools ported (pack load, API smoke, Supabase, push test, flags, crash reports, scoreboard, store listing, render jobs).
- [x] **REM-02**: Remaining skills ported (uplift, dispatch, bootstrap, memory, docs, packs ceiling, contract-first, gateway usage, doctor, receipts).
- [x] **REM-03**: Seat prompts, templates, roster JSON, ownership, and contract versions merged into Omega Prime contracts.

## Hardening

- [x] **HRD-01**: Per-pack eval cases assert behaviour + refusals deterministically.
- [x] **HRD-02**: Receipts close the loop end to end (claim cites commands + exit codes; no self-approval).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LEAD-01 | Phase 26 | Done |
| LEAD-02 | Phase 26 | Done |
| LEAD-03 | Phase 26 | Done |
| SYS-01 | Phase 27 | Done |
| SYS-02 | Phase 27 | Done |
| WEB-01 | Phase 28 | Done |
| WEB-02 | Phase 28 | Done |
| WEB-03 | Phase 28 | Done |
| MOB-01 | Phase 29 | Done |
| MOB-02 | Phase 29 | Done |
| MOB-03 | Phase 29 | Done |
| INF-01 | Phase 30 | Done |
| INF-02 | Phase 30 | Done |
| QUA-01 | Phase 31 | Done |
| QUA-02 | Phase 31 | Done |
| QUA-03 | Phase 31 | Done |
| REM-01 | Phase 32 | Done |
| REM-02 | Phase 32 | Done |
| REM-03 | Phase 32 | Done |
| HRD-01 | Phase 33 | Done |
| HRD-02 | Phase 33 | Done |

**Coverage:**

- v5 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-10-03 (v5 milestone)*
