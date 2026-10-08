# Phase 59 — Repository hardening — SUMMARY

## What was done

Brought the repository to enterprise-grade open-source shape for the v10
"Prime merge" milestone: AGPL-3.0 relicense, the full root file set, a
rewritten README documenting the Hermes+Omp+Prime architecture, merge
documentation, and supply-chain CI on both ecosystems.

### Relicense (REPO-01)

- `LICENSE` now carries the full GNU AGPL v3 text with a header block
  reading "Copyright (C) 2026 Spectrum Web Co". The v6 MIT decision is
  superseded by the explicit 2026-10-08 user request; the CHANGELOG
  records the relicense prominently under v10 "Changed".
- `pyproject.toml`: `license = "AGPL-3.0-only"`, authors Spectrum Web Co,
  AGPL classifier, description now mentions the Prime merge.
- All 23 Python source files created in v10 (Phases 55–58) carry
  `# SPDX-License-Identifier: AGPL-3.0-only` headers. Ported Prime code
  retains MIT attribution via `VENDOR.md` and module docstrings ("Adapted
  from …"), per the existing convention.
- `test_public_repo.py` asserts the AGPL text, copyright line, pyproject
  license field, and SPDX headers on every v10-created module.

### Root file set (REPO-02)

- Added `.github/CODEOWNERS` (`* @swcstudiospace` — the repo owner's
  verifiable GitHub org slug, per the remote `swcstudiospace/omes-bot`).
- Added `.github/dependabot.yml` covering pip and github-actions
  ecosystems. Cargo is deliberately excluded: `prime-agent/` is an
  ignored upstream checkout pinned in `VENDOR.md`, not a dependency.
- Already present and kept current: README, CHANGELOG, CONTRIBUTING,
  CODE_OF_CONDUCT, SECURITY, VENDOR, .gitignore, .gitattributes,
  .editorconfig, .gitbook.yaml, issue/PR templates (v8 set).

### Merge docs (REPO-03)

- `docs/adr/0001-prime-merge-architecture.md` — the port-vs-embed
  decision with the no-PyO3 evidence (verified: no pyo3/maturin anywhere
  in the pinned prime-agent tree; one-Python-process rule).
- `docs/connectors.md` — adapter contracts, error semantics
  (`PrimeError` wire shape), schema versioning, decode discipline.
- `docs/agent-loop.md` — the upgraded loop: goals, heartbeats, autonomous
  driver, session messaging, degraded mode via `prime_degraded` events.
- `docs/migration.md` — pre-v10 → v10: families config-gated default
  off, license change, new tool families.
- `docs/SUMMARY.md` updated (new `adr/` subsection); GitBook structure
  stays valid. `test_docs.py` now rglobs so the `adr/` subdirectory is
  covered by the docs gate.
- Stale counts fixed in `docs/architecture.md`, `build-aesthetics.md`,
  `setup.md`, `user-guide.md`, `tool-host.md` (135 tools / 108 default /
  23 families, per the v9 no-counts-in-prose rule where prose would rot —
  counts live only in generated/reference docs).

### Supply chain (REPO-04)

- `.github/workflows/supply-chain.yml` — pip-audit over the Python
  dependency set. Ran locally before committing: clean (the only finding
  was the venv's own pip 24.0 — environmental, not a project dep).
- cargo-deny (including `cargo deny check licenses` against prime-agent's
  own `deny.toml`) lives in the Phase 54 `rust-parity.yml` workflow;
  dependabot covers pip + github-actions. Both ecosystems covered, per
  the requirement, with the cargo exclusion documented.
- `test_public_repo.py::test_dependabot_and_supply_chain_cover_both_ecosystems`
  guards the wiring.

### README (REPO-05)

Rewritten end-to-end: what Omega Prime is; the three-source architecture
(Hermes loop + Omp harness + Prime RLM/harness in one Python agent) with
a text diagram; feature list; quickstart; dual-toolchain build
(Python package; Rust parity oracle via the pinned checkout, including
the three `--skip` flags for the known-failing `pa-cli acp_mode_e2e`
timing tests); configuration reference for `omega-prime.json`
(`PRIME_FAMILIES`, default-off). AGPL badge. No pinned test counts in
prose (v9 rule).

**Accuracy gate — every documented command executed:**

- `pip install -e '.[dev]'` → exit 0.
- `python -m omega_prime.setup_check --root .` → ok.
- `python -m omega_prime.mcp_server` → serves.
- `cargo build --locked` (pinned prime-agent checkout) → finished OK.

### Housekeeping

- `agent/goals.py`: `self._prime` and `_load_sidecar` annotated
  `dict[str, Any]` (editor-inference cleanliness; mypy already passed).
- `CHANGELOG.md`: v10 section (Added/Changed with the relicense).
- `test_public_repo.py`: 10 tests passed (AGPL assertions, new
  REQUIRED_FILES, SPDX gate, ecosystem gate).

## Requirements

- REPO-01: Done. REPO-02: Done. REPO-03: Done. REPO-04: Done.
  REPO-05: Done.
