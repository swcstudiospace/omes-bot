---
phase: 50-provider-protocols
plan: "01"
subsystem: api
tags: [responses, streaming, providers]
requirements-completed: [PCUR-03, PCUR-04]
completed: 2026-10-07
status: complete
---

# Summary 50-01: Responses mode + streaming

**Added OpenAI Responses routing/fallback and streamed conversation turns.**

## What was built

- **Responses**: `OpenAIProvider.api_mode` auto/responses/chat_completions;
  auto routes Responses on api.openai.com, chat elsewhere; Grok pinned to
  chat. Stateless `store: false` requests; transcript → input items;
  output items → assistant row (text + function_call; reasoning skipped;
  failed raises, incomplete parses). Shape-sniffing parse; Responses usage
  keys mapped. One-shot chat fallback on 404/scope-denied keys with
  `last_fallback` recorded; 400 and chat-mode errors surface directly.
- **Streaming**: `Transport.stream` yields text lines; HttpTransport does
  real SSE line iteration (retries end at first byte); FakeTransport
  replays scripted lines. Per-provider `stream_request` + `parse_stream`
  → (row, usage?) for OpenAI-shape (incl. usage chunk), Anthropic
  deltas, Gemini SSE, Ollama NDJSON. `ProviderModel(stream=True)` drives
  it; the loop consumes it unchanged.
- Tests: routing, round trip, failed/empty/incomplete, fallback ×3,
  stream wire shapes, 4 streaming accumulations, transport-no-stream,
  HTTP stream ×2, loop end-to-end. +14 total.
- Deferred (noted in code): Responses streaming, reasoning continuity.

## Verification

Suite → exit 0, 344 passed (330 + 14). Evals → 23 passed. Assemble,
ruff, mypy green. No live calls. Commit `cafcf5f`.
