# Phase 59: Repository hardening - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous

<domain>
## Phase Boundary

Bring the repository to state-of-the-art, enterprise-grade open-source
shape: AGPL-3.0 relicense with the exact copyright line, the full root
file set, a rewritten README documenting the Hermes+Omp+Prime
architecture, merge documentation (ADR, connectors, loop, migration), and
supply-chain CI on both ecosystems. In scope: LICENSE, root files,
README, docs/, .github/ templates + dependabot + audit jobs. Out of
scope: capability code (55–58), changing the Python CI gates (v9 owns
them), publishing anywhere.

</domain>

<decisions>
## Implementation Decisions

1. **License:** full GNU AGPL v3 text as `LICENSE`; copyright line
   "Copyright (C) 2026 Spectrum Web Co". New source files carry
   `SPDX-License-Identifier: AGPL-3.0-only`. Ported Prime/Hermes/Omp code
   retains its MIT attribution via VENDOR.md and file-header notes where
   a module is a close port (the existing convention: module docstrings
   already say "Adapted from Hermes …"). The v6 MIT decision is
   superseded by the explicit 2026-10-08 user request; CHANGELOG records
   the relicense prominently.
2. **Root files — audit, don't fabricate.** Present today: README.md,
   CHANGELOG.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, LICENSE,
   SECURITY.md, VENDOR.md, .editorconfig, .gitattributes, .gitignore,
   .gitbook.yaml, pyproject.toml. Missing per the enterprise set:
   CODEOWNERS (needs a confirmed owner handle — use the repo owner's
   GitHub team slug only if verifiable, otherwise document the skip in
   the SUMMARY, the v8 precedent), issue/PR templates, dependabot.yml.
   No fabricated badges/links/integrations.
3. **README rewrite:** what Omega Prime is; the three-source architecture
   (Hermes loop + Omp harness + Prime RLM/harness in one Python agent)
   with a text diagram; feature list; quickstart; build-from-source for
   both toolchains (Python package; Rust parity oracle via the pinned
   checkout); configuration reference (the new `omega-prime.json`).
   Every documented command is executed from the repo and passes before
   the phase closes (accuracy gate).
4. **Merge docs:** `docs/adr/0001-prime-merge-architecture.md` (the
   port-vs-embed decision with the no-PyO3 evidence), `docs/connectors.md`
   (adapter contracts, error semantics, versioning), `docs/agent-loop.md`
   (the upgraded loop: goals/heartbeats/autonomous/messaging, degraded
   mode), `docs/migration.md` (pre-v10 → v10: config flags default off,
   license change, new tools). GitBook `SUMMARY.md` updated; structure
   stays valid.
5. **Supply chain:** dependabot.yml (pip, github-actions; cargo is
   excluded — prime-agent is an ignored upstream checkout, not a
   dependency); pip-audit job (Python deps); the cargo-deny job lives in
   the Phase 54 rust-parity workflow. License-compatibility check:
   `cargo deny check licenses` against prime-agent's own deny.toml +
   pip license scan documented in SECURITY/CONTRIBUTING.

</decisions>

<code_context>
## Existing Code Insights

- v8 shipped the public-launch file set; v9 kept docs truthful
  (claim-by-claim verification convention).
- `.gitbook.yaml` + `docs/SUMMARY.md` — GitBook Git Sync structure must
  stay valid.
- Existing CI: `.github/workflows/ci.yml` (receipt-wrapped),
  `kb-refresh.yml` (scheduled), plus Phase 54's `rust-parity.yml`.
- `omega_prime/tests/test_public_repo.py` exists (v8) — root-file
  assertions extend there.

</code_context>

<specifics>
## Specifics

**Acceptance:** v10-REQUIREMENTS REPO-01..05. Verification: full gate
suite green; every README/docs command executed; workflows parse;
`test_public_repo.py` extended for the new root files.

</specifics>
