# Phase 47: Lint + format + types - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Ruff (`check` + `format`) and a pip-installable typechecker run clean on the
repo and are enforced in CI. Ruff is pinned exactly in a dev extra; the
checker runs via pip with no Node and no new global toolchain. All existing
gates stay green after the fixes.

Out: dependency floors/lockfile/matrix (Phase 48). Out: behavior changes —
lint/type fixes must not alter runtime behavior.
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Checker choice (mypy vs pyrefly): prefer the one
that installs cleanly here and reaches zero errors with the least
non-behavioral churn. Ruff rule set: explicit select, E501 left to the
formatter.

</decisions>

<code_context>
## Existing Code Insights

172 source files, no prior lint/type config. CI (`ci.yml`) has verify + docs
jobs; new jobs extend it. Check how existing tests assert CI contents before
adding gate tests.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (HYG-01, HYG-02, HYG-03).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
