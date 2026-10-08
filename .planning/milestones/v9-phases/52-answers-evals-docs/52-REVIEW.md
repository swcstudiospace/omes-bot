---
phase: 52-answers-evals-docs
reviewed: 2026-10-07
depth: deep
files_reviewed: 16
independent_feature_scope: 13
parent_cleanup_scope: 3
files_reviewed_list:
  - omega_prime/tools/substrate_tools.py
  - omega_prime/evals/runner.py
  - omega_prime/evals/cases/golden.json
  - omega_prime/evals/cases/redteam.json
  - omega_prime/tests/test_substrate_session.py
  - omega_prime/tests/test_mcp_server.py
  - omega_prime/tests/test_evals.py
  - omega_prime/tests/test_deps_matrix.py
  - omega_prime/tests/test_docs.py
  - omega_prime/tests/test_lint_types.py
  - docs/setup.md
  - docs/user-guide.md
  - docs/build-aesthetics.md
  - docs/tool-host.md
  - docs/tool-catalog.md
  - CHANGELOG.md
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 52: Code Review Report (re-review)

**Reviewed:** 2026-10-07
**Depth:** deep — current source after 52-REVIEW-FIX.md integration
**Files Reviewed:** 16 paths: 13 independently deep-reviewed feature paths plus three parent-reviewed audit-cleanup paths (including one deletion).
**Status:** clean

## Summary

All five pre-fix findings (CR-01, CR-02, WR-01, WR-02, WR-03) are closed in
the current source. `docs_search` exports a single bounded, sanitized
`chunks` representation with no raw payload, typed/redacted IDs, safe
positions, finite scores, and redacted bounded errors; malformed successes
are errors distinct from genuine empty results; the mark evals dispatch
through production ultrathink registration with a hermetic runner and an
approval-removal sensitivity regression; prose counts are truthful and the
catalog description matches. Deep cross-file tracing of the actual
registry/MCP consumers found no residual outward-facing leak and no new
plausible consumer bug. No product edits, commits, or test/gate reruns were
performed by this reviewer.

## Closure evidence (current source)

### CR-01 (raw retrieval leak) — CLOSED

- `omega_prime/tools/substrate_tools.py:79-83` — success returns only
  `redact_value({"chunks": _chunks(raw)})`; the raw retrieval body is never
  exported. The docstring at lines 81-82 states this explicitly.
- Tests pin the absence at the dispatch boundary
  (`omega_prime/tests/test_substrate_session.py:219,257`) and at the MCP boundary
  (`omega_prime/tests/test_mcp_server.py:203`), asserting `"retrieval" not in`
  the decoded payload/text on both success paths.
- Tool description (`omega_prime/tools/substrate_tools.py:274-278`) promises only
  "redacted excerpt chunks with provenance", and the regenerated catalog
  (`docs/tool-catalog.md:844`) carries the same contract. No source
  consumer references a `retrieval` key on the shaped result (grep
  `omega_prime/` confirms only docstrings and the negative test assertions).
- Citation provenance survives without the raw branch: explicit
  `chunk_id`/`document_id` (`substrate_tools.py:181-184`) and bounded
  `positions` (`186-199`) are asserted end-to-end
  (`test_substrate_session.py:220-234`).

### CR-02 (metadata/error redaction bypass) — CLOSED

- Every exported value is sanitized: per-field `redact_text` plus
  `_LABEL_CAP` on `document`/`dataset_id`/IDs (`substrate_tools.py:143-184`),
  and a final recursive `redact_value` over the whole success
  (`113`) and every error branch (`91-112`). `redact_value` recurses
  through dicts/lists/tuples (`omega_prime/credentials/redact.py:52-60`).
- `score` keeps only finite numbers (`substrate_tools.py:165-170`):
  `bool`/strings rejected, non-finite floats become `None`, zero survives
  as `0`. Pinned by `test_docs_tool_validates_metadata_types_and_preserves_zero`
  (`test_substrate_session.py:267-303`).
- All three error branches (RAGflow nonzero code, plane `ok:false`,
  transport exception) redact and cap at `_ERROR_CAP`
  (`substrate_tools.py:89-110`); whole-serialized assertions cover all
  three with a `ghp_`-shaped marker
  (`test_substrate_session.py:305-341`). MCP error flagging derives from
  the `"error"` key (`omega_prime/mcp_server.py:238`), exercised for both success
  and malformed paths (`test_mcp_server.py:199-214`).
- Positions admit only `type(coordinate) is int` (excludes `bool`),
  `coordinate >= 0`, shape 1-5, first 32 entries
  (`substrate_tools.py:186-199`).

### WR-01 (malformed success masquerading as empty) — CLOSED

- `_raw_chunks` (`substrate_tools.py:116-132`) returns `None` for
  absent/null/wrongly-typed bodies and containers, including non-dict
  `data`, dict-shaped `chunks`, and non-int `code` (with `bool` excluded
  at `99-100`). `None` maps to a redacted `malformed response` error
  (`111-112`).
- Genuine `[]` remains a valid empty success; nested `data.chunks` and
  top-level `chunks` both supported (`126-131`). Matrix of 11 malformed
  envelopes plus valid-empty and top-level-fallback controls in
  `test_docs_tool_malformed_response_is_error_not_empty`
  (`test_substrate_session.py:343-387`).

### WR-02 (self-declared mark approval) — CLOSED

- `omega_prime/evals/runner.py:147-187` dispatches mark cases through production
  `register_ultrathink_tools` (which derives `requires_approval` from
  `APPROVAL_TOOLS`, `omega_prime/tools/ultrathink.py:31-38,173-174`) with an
  injected hermetic CLI runner; `calls` records one entry per runner
  invocation, proving handler execution on approval and zero calls on
  refusal.
- Case files carry `family: ultrathink` with no `requires_approval`
  self-declaration (`golden.json:150-161`, `redteam.json:170-181`).
- Sensitivity regression
  (`omega_prime/tests/test_evals.py:64-85`) removes `ult_session_mark` from the
  real `APPROVAL_TOOLS` set and requires the red-team case to fail
  (via missing `approval required` refusal / unexpected call), then
  confirms both cases pass with production approval restored.

### WR-03 (stale guard counts) — CLOSED

- `docs/build-aesthetics.md:45-51` no longer pins numeric test/eval
  totals; it describes coverage structurally and states "CI reports the
  current test/eval totals; prose does not pin changing counts."
- Roster/MCP counts read true: 109 rostered (`docs/setup.md:37-38`,
  `docs/user-guide.md:36-39`, `docs/build-aesthetics.md:20`) and 108
  MCP-served (`docs/tool-host.md:12-14`), matching the supplied setup
  smoke (108 served tools).

## Deep cross-file checks (no new findings)

- Registry `dispatch` JSON-encodes the handler dict unchanged
  (`omega_prime/tools/registry.py:83-84,163-164`); MCP wraps that string with
  `is_error = "error" in decoded` (`omega_prime/mcp_server.py:237-241`). Since
  the shaped result contains no raw copy and all strings are pre-redacted,
  neither layer reintroduces the leak.
- `ApprovalLog.approve` is name-based (`omega_prime/tools/approvals.py:19-44`),
  so the sensitivity test's mechanism (scrubbing `APPROVAL_TOOLS` flips
  the registered `requires_approval` flag while the golden `approve:true`
  still records) is coherent: removal breaks the unapproved red-team case
  while the approved golden case keeps passing.
- `omega_prime/tests/test_substrate.py:218-221` asserts raw-envelope passthrough
  at the transport-client layer (`client.docs_search`), not at the
  model-facing tool layer — correct layering, not a CR-01 recurrence.
- Caps compose safely: redaction shortens secret-shaped values to
  `[REDACTED]`, so post-redaction slicing plus the outer `redact_value`
  keeps `content ≤ 1500`, labels/IDs ≤ 500, errors ≤ 500, as pinned by
  the length assertions in the whole-result tests.

## Requirement assessment

| Requirement | Assessment | Evidence |
| --- | --- | --- |
| DPT-04 | Satisfied | Single sanitized excerpt representation; no raw export; typed/redacted IDs, safe positions, finite scores; redacted bounded errors |
| EVAL-01 | Satisfied | Mark evals use production registration + hermetic runner; approval-removal sensitivity regression present |
| EVAL-02 | Satisfied | 109/108 counts truthful; no stale totals; catalog description matches tool schema |

## Verification basis (explicitly distinguished)

- **Supplied runtime evidence (not rerun by this reviewer):**
  `local://omes-v9-gate-evidence.md` — 354 pytest passed, 26/26 evals,
  ruff check/format, mypy 175 files, setup smoke (108 tools), catalog
  freshness, and the throwaway decoder→registry→MCP/conversation-loop
  smoke (no raw retrieval, no synthetic secret, NaN→null, malformed vs
  empty distinct, error redacted, `live_calls=0`). Per the assignment
  contract, gates were not rerun mid-flight; `52-REVIEW-FIX.md` is
  retained as provenance for the fix slices.
- **Own work (static only):** full read of `omega_prime/tools/substrate_tools.py`
  (1-333), `omega_prime/evals/runner.py`, the mark-case JSON extracts, the
  substrate/MCP/eval test bodies cited above, plus consumer tracing
  through `omega_prime/tools/registry.py`, `omega_prime/mcp_server.py`,
  `omega_prime/credentials/redact.py`, and `omega_prime/tools/ultrathink.py`
  (APPROVAL_TOOLS/registration). Test sensitivity and boundary coverage
  were inspected statically; their green status is taken from the
  supplied evidence. No probes, builds, linters, or live calls were run.

## Parent supplemental audit cleanup

The parent subsequently removed ten incidental tests: five configuration/
source-spelling tests (deleting `test_lint_types.py`), four version/configuration
copy tests from `test_deps_matrix.py`, and the heading/sync-source test from
`test_docs.py`. Complete/resolvable navigation and the actual missing-Discord
controlled failure remain covered.

Parent read all removed statements and checked all ten test functions with
LSP: only their own declarations were referenced. No runtime implementation
changed. Final observed gates: 344 tests, 26 evals, Ruff lint/format (205 files),
mypy (174 files), assembly, setup (108 served tools), catalog, and pip check
all pass. This supplements the independent 13-file review; it is not claimed
as another subagent run or a live probe. No new Phase 52 finding identified.

The separate milestone security audit has two open high SSRF findings in
Phase 46. This clean Phase 52 code review does not close or accept those risks.

## Disposition

Clean. No BLOCKER or WARNING findings in the current source. No follow-up
code changes required from this review.

---

_Reviewed: 2026-10-07_
_Reviewers: Phase52ReReview (gsd-code-reviewer, 13-file independent scope); parent (three-path supplemental audit cleanup)_
_Depth: deep (static; runtime verdicts per supplied gate evidence)_
