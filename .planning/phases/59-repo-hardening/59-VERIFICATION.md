---
phase: 59-repo-hardening
verified: 2026-10-08
status: passed
score: 5/5 repository criteria verified
gaps: []
---

# Verification: Phase 59 Repository hardening

**Status:** passed
**Date:** 2026-10-08

## Success criteria

1. `LICENSE` is the GNU AGPL-3.0 text with "Copyright (C) 2026 Spectrum Web
   Co"; the 23 v10 modules carry SPDX `AGPL-3.0-only` headers; ported Prime
   code keeps its MIT attribution in `VENDOR.md` — PASS
   (`test_public_repo.py::test_packaging_is_public_complete`,
   `test_new_v10_modules_carry_spdx_headers`).
2. Root file set present and non-trivial — PASS
   (`test_required_files_exist_and_nontrivial`, including CODEOWNERS,
   dependabot, issue/PR templates, supply-chain workflow).
3. `docs/adr/0001-prime-merge-architecture.md`, `docs/connectors.md`,
   `docs/agent-loop.md`, and `docs/migration.md` exist; GitBook links stay
   valid — PASS (those paths are in `REQUIRED_FILES`; `test_docs.py` is in
   the suite).
4. Supply-chain CI covers the committed Python lock and the pinned Rust
   workspace — PASS. `cargo deny check licenses` is in `rust-parity.yml`
   and was re-run this closeout. pip-audit reads `requirements-lock.txt`.
   Dependabot covers pip and github-actions. Cargo dependabot is omitted
   because `prime-agent/` is an ignored, pin-locked checkout, not a
   committed Cargo project.
5. README documents the Hermes + Omp + Prime architecture, quickstart,
   dual toolchain, and `PRIME_FAMILIES` config — PASS. Documented commands
   below were executed.

## Commands

- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 528 passed,
  12 warnings.
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` →
  exit 0, 26 passed, 0 failed.
- `.venv/bin/ruff check omega_prime` → exit 0. `.venv/bin/ruff format
  --check omega_prime` → exit 0, 246 files already formatted.
- `.venv/bin/python -m mypy omega_prime` → exit 0, no issues in 215 source
  files. The `mypy` console script's shebang still points at
  `/root/src/repos/Omes-Bot/.venv/bin/python3`; CI invokes `python -m mypy`.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- `.venv/bin/python -m omega_prime.tooling.catalog --check` → exit 0.
- `.venv/bin/python -m omega_prime.setup_check --root .` → exit 0, registry
  serves 108 roster tools.
- `.venv/bin/python -m pip_audit --progress-spinner off -r
  requirements-lock.txt --ignore-vuln PYSEC-2026-4114` → exit 0, "No known
  vulnerabilities found, 1 ignored".
- `cargo-deny 0.20.2 check licenses` in `prime-agent/` → exit 0,
  `licenses ok`.
- `.venv/bin/python -m pytest omega_prime/tests/test_public_repo.py -q` →
  exit 0, 9 passed.

## Notes

- PYSEC-2026-4114 is an oauthlib authorization-server PKCE timing oracle.
  tweepy 4.17 requires `oauthlib>=3.2.0,<4`. This process does not host
  that grant. The ignore is recorded in `SECURITY.md` and in
  `.github/workflows/supply-chain.yml`.
- A bare `pip-audit` of the local virtualenv also reports pip 24.0
  advisories and a leftover `omes-bot` editable dist-info. Neither is a
  lockfile entry. CI audits the lockfile.
- Auditing the installed environment without `--ignore-vuln` exits 1 on
  PYSEC-2026-4114. The workflow command above is the one CI runs.

## Requirements

- REPO-01: Done. REPO-02: Done. REPO-03: Done. REPO-04: Done. REPO-05: Done.
