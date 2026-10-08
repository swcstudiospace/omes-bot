# Phase 49: Provider resilience - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Provider requests retry transient failures with backoff; per-turn token
usage is recorded and visible; provider defaults are current (raised
Anthropic max_tokens, refreshed model IDs). Tests run behind FakeTransport
with no live calls. No protocol additions (Responses/streaming are
Phase 50).

Out: new providers, new transports, live verification.
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Retry policy (which errors, how many attempts,
backoff shape) and usage record shape follow provider-API conventions and
stay injectable/testable (no real sleeping in tests).

</decisions>

<code_context>
## Existing Code Insights

Providers take `model` as a parameter (no hardcoded defaults in
`providers/`); defaults live in docs/agent config — find them during
planning. `ProviderModel` drives the loop; `Transport` is post/get JSON;
base docstring admits no retries/streaming/usage.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (PCUR-01, PCUR-02, PCUR-05).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
