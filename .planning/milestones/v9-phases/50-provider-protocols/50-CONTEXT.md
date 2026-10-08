# Phase 50: Provider protocols - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

The OpenAI provider speaks the Responses API on api.openai.com with
automatic chat_completions fallback; xAI/compatibles stay on
chat_completions. The loop consumes streamed provider output end to end
behind a streaming fake. Tests stay hermetic with no live calls.

Out: Responses streaming (chat-shape streaming only), reasoning-item
continuity (stateless store:false), new providers.
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was
skipped per user setting. Routing, fallback triggers, stream framing split
(transport lines vs provider parse), and usage-in-stream follow the
conventions found in planning (ecosystem: Responses default on first-party
endpoints, fallback on scope-denied keys; stateless loop owns the
transcript).

</decisions>

<code_context>
## Existing Code Insights

`api_mode` is declarative-only (never read) — safe to evolve. `Transport`
is post/get JSON; streaming adds a line-iterator method with fakes on both
sides. `ProviderModel.complete` is the single POST site — the fallback and
stream flag both land there. Responses failed/incomplete statuses and
reasoning items need explicit handling, not crashes.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase
description and success criteria (PCUR-03, PCUR-04).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
