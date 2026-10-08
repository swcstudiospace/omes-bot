# Features Research: v9 SOTA upgrade

**Date:** 2026-10-07
**Mode:** Inline (GSD research agents unavailable in this runtime)

## Table stakes (SOTA agents have these; Omega Prime lacks them)

- **Lint + format enforced**: `ruff check` / `ruff format --check` in CI.
- **Types enforced**: a checker in CI with zero errors on `omega_prime/`.
- **Pinned dependencies**: floors at verified versions + a committed lockfile.
- **Provider retries**: transient-failure retry with backoff (base.py docstring admits none).
- **Usage accounting**: tokens/cost per turn visible (docstring admits none).
- **Hermetic tests**: no test writes outside the repo/tmp (PyRIT writes to `~/.local/share` today).

## Differentiators (worth doing)

- **Responses API mode** for the OpenAI provider (default per OpenAI); keep
  chat_completions for xAI/compatibles.
- **Streaming transport**: token-stream from provider to loop (Transport is
  post/get-JSON only today); enables live progress + lower time-to-first-token.
- **PyRIT orchestrator depth**: multi-turn orchestrators + scorer-based judging
  (deferred in v4; keyless deterministic subset stays in CI).
- **docs_search chunk extraction** (deferred in v7: returns raw payload today).
- **Python 3.13/3.14 in CI matrix** with the discord import guarded.

## Anti-features (do NOT do)

- Live API calls in committed tests — violates hermetic rule + user decision.
- Marketplace/GitBook-dashboard actions — user steps, not code.
- Multi-seat channel mechanics — out of scope since v1.
