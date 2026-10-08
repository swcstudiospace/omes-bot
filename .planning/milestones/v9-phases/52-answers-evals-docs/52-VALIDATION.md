---
phase: "52"
slug: "52-answers-evals-docs"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-07"
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Reconstructed post-hoc (validate-phase State B: no VALIDATION.md existed at
> execution; SUMMARY exists). No new tests were needed — every requirement maps
> to existing behavioral tests, green per the parent-exercised gates recorded in
> `local://omes-v9-gate-evidence.md`. This validator ran no gates itself per task
> contract; results below are supplied receipts plus code-backed mapping.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (observed `.venv/bin/pytest --version`; config: `pyproject.toml` `[tool.pytest.ini_options]`, `testpaths = ["omega_prime/tests"]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest omega_prime/tests/test_substrate_session.py omega_prime/tests/test_evals.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider` |
| **Measured runtime** | 24.49 s (final parent full-suite receipt: 344 passed) |

Additional gates (all exit 0 per supplied receipts): `omega_prime.evals.runner
omega_prime/evals/cases`, `bash omega_prime/scripts/assemble-prompts.sh --check`,
`.venv/bin/ruff check omega_prime/`, `.venv/bin/ruff format --check omega_prime/`,
`.venv/bin/mypy omega_prime/`, `.venv/bin/python -m omega_prime.setup_check --root .`,
`.venv/bin/python -m omega_prime.tooling.catalog --check`.

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

Plan 52-01 is a single-wave plan (wave 1); rows map each requirement to its
automated verification. Targeted pytest commands below are reusable selectors;
their tests passed within the observed full suite, not separate targeted runs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 52-01-DPT04-chunks | 01 | 1 | DPT-04 | T-52-01 / T-52-02 / T-52-03 / T-52-05 | Chunk-only excerpts; whole-result redaction; 1500-char cap; bounded redacted metadata/IDs/positions; finite scores; redacted bounded errors; malformed ≠ empty | unit + MCP boundary | `.venv/bin/python -m pytest omega_prime/tests/test_substrate_session.py omega_prime/tests/test_mcp_server.py -q` | ✅ | ✅ green (in final 344-passed suite) |
| 52-01-EVAL01-marks | 01 | 1 | EVAL-01 | WR-02 | Mark evals derive approval from production registration; removal breaks red-team eval; empty allow-list denies by default | unit (sensitivity) + eval CLI | `.venv/bin/python -m pytest omega_prime/tests/test_evals.py -q` and `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` | ✅ | ✅ green (26 passed, 0 failed) |
| 52-01-EVAL02-docs | 01 | 1 | EVAL-02 | WR-03 | Prose states 109 roster / 108 MCP-served tools; no brittle totals; catalog regenerated and fresh | navigation + executable generators | `.venv/bin/python -m pytest omega_prime/tests/test_docs.py -q`, `.venv/bin/python -m omega_prime.setup_check --root .`, `.venv/bin/python -m omega_prime.tooling.catalog --check` | ✅ | ✅ green (in final 344-passed suite; both CLIs exit 0) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Requirement → test-file cross-reference:

- **DPT-04 → `omega_prime/tests/test_substrate_session.py`** (`test_docs_tool_returns_excerpts_without_raw`,
  `test_docs_tool_redacts_entire_payload_and_caps_content`,
  `test_docs_tool_validates_metadata_types_and_preserves_zero`,
  `test_docs_tool_redacts_every_error_branch`,
  `test_docs_tool_malformed_response_is_error_not_empty`) **+ `omega_prime/tests/test_mcp_server.py`**
  (`test_call_tool_substrate_docs_search_exports_no_raw_secret`): **COVERED**.
- **EVAL-01 → `omega_prime/evals/cases/golden.json` + `redteam.json`** (approved/unapproved
  `ult_session_mark` family cases, empty-policy deny case) **+ `omega_prime/evals/runner.py`**
  (`_run_ultrathink_family_case`) **+ `omega_prime/tests/test_evals.py`**
  (`test_shipped_cases_all_pass`, `test_mark_approval_removal_breaks_redteam_eval`): **COVERED**.
- **EVAL-02 → `docs/setup.md`, `docs/user-guide.md`, `docs/build-aesthetics.md`,
  `docs/tool-host.md`** (verified 109/108 prose) **+ `docs/tool-catalog.md`**
  (regenerated) **+ `CHANGELOG.md` + `omega_prime/tests/test_docs.py`** (complete, resolvable navigation)
  **+ `catalog --check` / `setup_check` gates**: **COVERED**.

Gap analysis: 0 gaps found, 0 resolved, 0 escalated. `nyquist_compliant: true` is
warranted — every requirement has automated behavioral verification, sampling is
continuous (single wave, all rows verified), no watch-mode flags, latency < 30 s.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 needed.

- [x] `omega_prime/tests/test_substrate_session.py` — covers DPT-04 (present before fix, extended by it)
- [x] `omega_prime/tests/test_evals.py` + `omega_prime/evals/runner.py` — covers EVAL-01
- [x] `omega_prime/tests/test_docs.py` + catalog/setup gates — covers EVAL-02
- [x] pytest + eval-runner + ruff + mypy + assemble + setup_check + catalog tooling installed and green

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live substrate docs search against a real RAGflow plane | DPT-04 | Live services are out of scope for the phase (phase boundary; roadmap "live probes manual opt-in") | Manual opt-in only; hermetic fakes + throwaway decoder smoke cover the contract |
| Live provider / ultrathink CLI execution | EVAL-01 | Same out-of-scope live boundary; hermetic injected runner covers approval wiring | Manual opt-in only |
| Visual docs rendering (GitBook sync) | EVAL-02 | Rendering is external to the repo | Open the published docs; confirm counts read 109/108 |

*None of the above blocks Nyquist compliance — the in-scope behaviors all have
automated verification; these are the standing manual opt-ins.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (single wave, 3/3 verified)
- [x] Wave 0 covers all MISSING references (no MISSING references)
- [x] No watch-mode flags
- [x] Feedback latency < 30 s (24.49 s full-suite test time; 27.2 s command time)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-07

## Validation Audit 2026-10-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 (manual-only rows above are standing opt-ins, not escalations) |
