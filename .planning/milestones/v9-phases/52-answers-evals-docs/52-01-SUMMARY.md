---
phase: 52-answers-evals-docs
plan: "01"
subsystem: api
tags: [retrieval, redaction, evals, docs]
requirements-completed: [DPT-04, EVAL-01, EVAL-02]
completed: 2026-10-07
status: complete
key-files:
  modified:
    - omega_prime/tools/substrate_tools.py
    - omega_prime/evals/runner.py
    - omega_prime/evals/cases/golden.json
    - omega_prime/evals/cases/redteam.json
    - omega_prime/tests/test_substrate_session.py
    - omega_prime/tests/test_mcp_server.py
    - omega_prime/tests/test_evals.py
    - omega_prime/tests/test_deps_matrix.py
    - omega_prime/tests/test_docs.py
    - docs/setup.md
    - docs/user-guide.md
    - docs/build-aesthetics.md
    - docs/tool-host.md
    - docs/tool-catalog.md
    - CHANGELOG.md
  removed:
    - omega_prime/tests/test_lint_types.py
---

# Summary 52-01: Chunked answers + eval growth + truthful docs

**Docs answers use safe excerpts; v9 evals exercise real mark approval; docs and catalog match the runtime.**

## What was built

- DPT-04: only extracted `chunks` leave docs search. Content is redacted and capped at 1500 characters. Document/dataset strings and optional chunk/document IDs are typed, redacted, and capped at 500 characters; finite numeric scores preserve zero. Citation positions retain only bounded lists of nonnegative integer coordinates. No arbitrary vendor payload is copied.
- RAGflow, substrate-plane, and transport errors are redacted and bounded. Missing or malformed body/chunk containers return errors; nested/top-level chunk lists and genuine empty lists remain supported.
- EVAL-01: approved/unapproved ultrathink mark cases now use production family registration and an injected hermetic runner. Production approval removal makes the red-team eval fail. The empty-policy allowlist case remains deny-by-default. Generic existing cases keep their original mode.
- EVAL-02: setup, user guide, tool host, and build documentation reflect 109 rostered tools and 108 MCP-served tools. Removed stale numeric test/eval promises; regenerated the tool catalog after correcting the retrieval description. Changelog records v9 changes.
- Replaced raw-preservation, case-count/ID pins, and source-text/wiring assertions with consumer-visible retrieval and approval sensitivity coverage.
- Audit cleanup removed configuration/CI-source/MCP-spelling/version-copy tests and heading/sync-source assertions. Retained resolvable, complete navigation and the actual missing-Discord controlled failure; executable gates verify the removed proxies' intended contracts.

## Review corrections

CR-01 and CR-02: raw retrieval removed; all exported metadata/errors sanitized, including explicit citation fields. WR-01: malformed success no longer masquerades as an empty result. WR-02: mark evals derive approvals from real registration. WR-03: stale prose counts removed.

## Verification

- Final post-cleanup suite: 344 passed, no skips, 12 existing dependency deprecation warnings (exit 0). The earlier integrated run passed 354 tests; removing ten incidental proxy tests accounts for the difference without narrowing behavioral cases.
- Deterministic eval CLI: 26 passed, 0 failed (exit 0).
- Prompt assembly, Ruff lint, Ruff format (205 files), mypy (174 files), setup smoke (108 served tools), catalog freshness, and `pip check`: exit 0.
- A post-fix throwaway smoke exercised the real substrate decoder → registry → MCP and conversation loop → next model request. Whole outputs excluded synthetic secret markers and text beyond the excerpt cap; safe citations survived; non-finite scores were omitted; malformed, empty, and error responses had the correct MCP status. No live service calls.
- A mypy inference error in the heterogeneous malformed-envelope fixture was corrected with an explicit list annotation; the type gate then passed. This annotation does not alter test behavior.
- Independent re-review and goal verification pass for the Phase 52 feature changes. Parent reviewed the three audit-cleanup paths inline with LSP reference checks and reran executable gates. Phase 52's five security threats are closed; the milestone is blocked by two newly audited Phase 46 SSRF gaps, not accepted risks.

## Deviations and limits

- Resumed the existing plan/implementation; did not rerun completed Phases 46–51 or overwrite their historical evidence. Repaired legacy verification/summary YAML metadata so canonical GSD discovery can read it.
- Fix work used two independent subagents; the parent integrated and ran all checks afterward.
- No commit, push, merge, branch change, or tag: saved PROJECT.md continuation instructions forbid Git mutations. Changes remain in the working tree. `commit_docs=false` and `git.create_tag=false` remain unchanged.
- Python 3.12.3 was exercised locally. Python 3.13/3.14 CI execution and live provider/substrate/ultrathink services were not exercised in this continuation.

## Self-Check

PASSED for Phase 52 implementation and automated runtime gates. Milestone advancement/archival remains blocked by T-46-08/T-46-12 pending a user security disposition.
