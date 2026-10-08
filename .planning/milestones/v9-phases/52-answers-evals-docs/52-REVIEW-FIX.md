---
phase: 52-answers-evals-docs
iteration: 1
status: fixed
fixed: 5
remaining: 0
commit_status: not_committed_per_project_instructions
---

# Phase 52 — Review Fixes

| Finding | Resolution | Exercised evidence |
|---|---|---|
| CR-01 | Removed raw retrieval; explicit redacted chunk/document IDs and bounded numeric positions preserve citations | Whole-result unit/MCP regressions and real decoder → next-model smoke; no beyond-cap sentinel or synthetic secret |
| CR-02 | Typed and bounded metadata, finite scores, recursive redaction on every success/error; bounded upstream errors | Whole-result metadata/error coverage in passing suite; MCP smoke redacted RAGflow error |
| WR-01 | Validate successful body/container shapes; errors differ from legitimate empty results | Malformed-envelope matrix and valid empty/fallback controls; MCP smoke error flags |
| WR-02 | Mark evals use production registration with hermetic runner, not self-declared approvals | 26 passing evals and approval-removal sensitivity regression in 354-test suite |
| WR-03 | Removed stale prose test/eval totals; regenerated tool catalog and updated roster/MCP docs | Docs tests, setup smoke, and catalog freshness passed |

Both fix slices skipped tests/formatters during their work. Parent integrated the changes and ran the gates once afterward; corrected one test-fixture type inference error and reran the type gate successfully. Existing source-text/count/ID/wiring assertions encountered in the edited eval tests were removed, not repinned.

No Git mutations were made: the saved continuation instructions prohibit commit/push/merge/tag and planning config has commit_docs=false. Independent re-review writes the current verdict to 52-REVIEW.md.
