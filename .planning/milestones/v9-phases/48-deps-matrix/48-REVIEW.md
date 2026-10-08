---
phase: 48-deps-matrix
reviewed: "2026-10-07"
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .github/workflows/ci.yml
  - omes/scripts/ci_receipt.py
  - docs/setup.md
  - .planning/phases/48-deps-matrix/48-REVIEW.md
  - .planning/phases/48-deps-matrix/48-02-SUMMARY.md
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: passed
---

# Phase 48: Code Review Report

**Reviewed:** 2026-10-07, native continuation
**Depth:** standard
**Files Reviewed:** 5
**Status:** passed — source review only

## Native continuation verdict

`P48HelperReview` independently reviewed the shared helper and workflow:
no material findings. WR-01 is closed by explicit absence handling for
numeric/string zero; IN-01 is closed by the shared stdlib helper.
Command failures, matrix/triggers, always-run fail-closed summaries, and
the actual named Discord guard requirement are preserved.

Main's 14 subprocess smoke scenarios and actionlint/Ruff evidence are
recorded in `48-02-SUMMARY.md`. Current helper LSP diagnostics report OK.
The reviewer ran no gates. Real final-candidate three-interpreter and
matching-head hosted CI acceptance remain pending; HYG-05 stays open.

## Historical review — preserved

Reviewed `.github/workflows/ci.yml` (528 lines; pre-edit baseline was 68 lines via `git show HEAD:.github/workflows/ci.yml`) as the Task 1 minimal CI receipt tracer. Checked every focus area: failure-as-pass paths, `set +e` exit-code capture under GitHub's default `bash -e` shell, `$GITHUB_OUTPUT` writes, the `always()` receipt state mapping, JUnit guard parsing, `${{ }}` injection, receipt information disclosure, and preservation of original gates/matrix/triggers/docs job.

No failure path reports a failed command as passed: every gated `run:` block starts with `set +e` as its first command (so GitHub's `-e` never aborts before capture), captures `rc=$?` immediately after the single gated command, publishes it to `$GITHUB_OUTPUT`, and ends with `exit "$rc"`, so the step outcome always equals the gated command's exit code. The three `always()` receipt summaries fail closed (`sys.exit(...)` when any blocker exists; the verify receipt additionally fails when the named guard is not `passed`), and a passing receipt cannot mask a prior step failure because the job conclusion still aggregates the failed step. All `${{ }}` interpolations live in `with:`/`env:` values only (matrix version, step outputs, `toJSON(steps)`, `job.status`); `run:` bodies use shell `$vars` and a quoted `<<'PY'` heredoc, so there is no expression-injection surface. Receipt output is exit codes, outcomes, versions, and runner paths only — no secrets or tokens. All original gate commands are preserved (verify: install / `pytest omes/tests -q` extended with `-rA --junitxml`, evals, assemble `--check`; lint: `.[dev]` install, ruff check, ruff format; types: mypy; docs: unchanged 3.12 single-leg job), as are the `3.12/3.13/3.14` matrices, `push`/`pull_request` triggers, action versions, and the separate docs job. The JUnit guard match (`classname == "omes.tests.test_deps_matrix"`, `name == "test_discord_module_imports_without_the_library"`) is consistent with pytest's path-derived JUnit `classname` for `omes/tests/test_deps_matrix.py` (verified the test exists; no `importmode` override in `pyproject.toml`, and JUnit classnames derive from the nodeid path regardless), and every STAGES inventory exactly matches its job's step `id`s. One latent robustness warning and one maintainability note below; no blockers.

## Historical warnings — resolved

### WR-01: Falsy exit-code mapping conflates observed-zero with unobserved

**File:** `.github/workflows/ci.yml:176,359,503`
**Issue:** Each receipt maps step outputs with `"exit_code": int(exit_code) if exit_code else None`. `exit_code` arrives via `toJSON(steps)` and is a string today, where `"0"` is truthy so observed-zero currently maps correctly. But if the value is ever numeric (or empty-string vs `0` handling changes), numeric `0` is falsy and would map to `None` — i.e., an observed clean exit would be recorded as "null exit when unobserved", corrupting the passed/with-code-0 evidence the tracer exists to provide.
**Fix:** Test for absence explicitly in all three receipt scripts:
```python
"exit_code": int(exit_code) if exit_code not in (None, "") else None,
```

## Historical information — resolved

### IN-01: Triplicated tracer/receipt blocks invite drift

**File:** `.github/workflows/ci.yml:22-140,233-324,386-468`
**Issue:** The identity/pip/install/resolved/pip-check tracer pattern and the ~40-line receipt-summary Python are repeated nearly verbatim across `verify`, `lint`, and `types` (only the tail stages and the verify-only JUnit guard differ). A future edit to one copy (e.g., the state mapping or the exit-code fix above) must be applied three times; the file grew from 68 to 528 lines almost entirely through repetition.
**Fix:** Deduplicate with YAML anchors for the repeated `run:` blocks, or extract the receipt summary into a composite action / shared script checked into the repo (e.g., `omes/scripts/ci-receipt.py`) invoked with the STAGES list as an argument.

---

_Reviewed: 2026-10-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
