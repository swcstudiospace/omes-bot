---
phase: "48"
slug: "deps-matrix"
status: verified
threats_open: 0
threats_total: 7
threats_closed: 7
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: "2026-10-07"
---

# Phase 48 — Security

## Trust Boundaries

declared packages/Python versions → imports/runtime; exact reproduction → compatible SDK contracts.

## Audit Scope and Evidence

Retroactive STRIDE: no plan-time threat register existed. Read-only security reviewer `V9SecurityGate` constructed the register before classifying mitigations. Parent writes this artifact; no risk acceptance, Git mutations, installs, or live calls occurred. This is scoped ASVS L1 control verification, not OWASP certification or an independent CVE scan.

Initial supplied receipts passed 354 tests; after removing ten incidental proxy tests, final parent gates passed 344 tests (no skips), 26 evals, assembly, Ruff lint/format (205 files), mypy (174 files), setup (108 served tools), catalog freshness, and pip check. The earlier actual decoder → registry → MCP / next-model consumer smoke remains valid because runtime code was unchanged by test-only cleanup. Historical phase evidence remains historical. Python 3.13/3.14 CI execution, live services, macOS PyRIT isolation, and external SQL-adapter privileges were not certified.

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-48-01 | Denial of service | Dependency/Python incompatibility | medium | mitigate | `pyproject.toml:21-29` declares raised floors; `.github/workflows/ci.yml:8-56` configures 3.12/3.13/3.14. Final `pip check` reports no broken requirements and actual SDK consumers pass in the 344-test suite. Configuration/version-copy proxies removed. No real 3.13/3.14 outcomes or fresh installation observed. | closed, L1 configuration |
| T-48-02 | Denial of service | Discord import failure breaks collection | medium | mitigate | `omes/tools/discord.py:16-19,44-47` catches missing-library import and refuses factory operation. `test_discord.py:10-13,228-238` and the retained real subprocess regression in `test_deps_matrix.py:13-34` cover controlled failure; final suite passes. Historical audioop simulation remains attributed to 48-VERIFICATION, not rerun. | closed, L1 |
| T-48-03 | Tampering | Unreproducible dependency set / MCP major drift | medium | mitigate | `requirements-lock.txt:1-150` records exact versions; `pyproject.toml:23` caps MCP below 3; `docs/tool-host.md:21-24` records wire conventions. Final dependency-consistency, actual MCP SDK tests, setup smoke, and catalog gates pass. Incidental pin-copy proxies removed. No hash-integrity, fresh-installation, or CVE-free claim. | closed, L1 |
| T-48-02-01 | Tampering | `.github/workflows/ci.yml` receipt steps (48-02) | high | mitigate | Plan-time register. Each of the 23 command steps starts with `set +e`, captures `rc=$?` right after its gated command and ends with `exit "$rc"`. The file has no `continue-on-error`, no `\|\| true` and no literal `exit 0`. The `always()` receipt summaries fail closed and keep raw outcome/conclusion/job status. `48-REVIEW.md` found no failure-as-pass path. WR-01 (warning) notes that `int(exit_code) if exit_code else None` would record a numeric 0 as null; Actions step outputs are strings today, so current behavior is correct. The finding is routed to the sole CI writer, not fixed here. | closed, L1 source; hosted runtime not observed |
| T-48-02-02 | Information disclosure | CI identity/install logs (48-02) | high | mitigate | No `secrets.` references, no token variables and no environment dump; `os.environ` reads are keyed only. Identity output is limited to allowlisted interpreter, checkout and GitHub/runner fields. `pip list --format=json` emits names/versions/editable locations. `48-REVIEW.md` confirms no secret disclosure and no `${{ }}` inside `run:` scripts. | closed, L1 source |
| T-48-02-03 | Denial of service | Matrix evidence loss on first failure (48-02) | medium | mitigate | `strategy.fail-fast: false` on verify, lint and types (lines 11, 222, 375; yaml parse confirms). A failed lane still fails the workflow. | closed, L1 source |
| T-48-02-SC | Tampering | pip installs, fresh resolve (48-02) | high | mitigate | Install inputs are unchanged (`-e . pytest` / `-e '.[dev]'`), now interpreter-bound. `pyproject.toml` and `requirements-lock.txt` SHA-256 equal the frozen 48-02 baseline. No new packages or pins. | closed, L1 source |

Only open high/critical threats count toward `threats_open`; threshold is high. Closed entries carry their stated L1/source/runtime limits, not an implied deeper certification.

## Accepted Risks Log

No accepted risks. All dispositions remain mitigate; the auditor cannot accept risk.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|------------|---------------|--------|---------------|--------|
| 2026-10-07 | 3 | 3 | 0 | V9SecurityGate (read-only specialist); parent artifact integration |
| 2026-10-07 (48-02) | 7 | 7 | 0 | Main secure-phase State A, L1 short-circuit (plan-time register, `threats_open: 0`, ASVS 1); evidence from source grep, `actionlint`, yaml parse and `48-REVIEW.md` |

## Sign-Off

- [x] Every threat has a disposition.
- [x] Accepted risks log records none.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set.

**Approval:** verified 2026-10-07, scoped ASVS L1.
