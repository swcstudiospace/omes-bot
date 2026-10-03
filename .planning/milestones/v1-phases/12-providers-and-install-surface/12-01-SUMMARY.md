---
phase: 12-providers-and-install-surface
plan: 01
subsystem: providers
tags: [providers, grok, openai, anthropic, gemini, ollama, install-surface]
provides:
  - Provider contract with five adapters behind an injected transport
affects: []
---

# Phase 12 summary

`ProviderModel` satisfies the turn loop's `Model` protocol over any `Provider` plus any `Transport`: build the request, POST, parse one assistant row. `GrokProvider` (xAI chat completions) subclasses the OpenAI-compatible wire; Anthropic, Gemini, and Ollama map their own endpoints, headers, and tool round-trips. `FakeTransport` replays scripted payloads and records every call, so no test touches a socket and a missing key raises before the transport. The install-surface test registers all five tool families and asserts the roster lists exactly the registry's names in family order, the template names nothing missing, the assembled prompt equals a fresh render, and a claim with no command fails the receipt check while a well-evidenced receipt passes.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `94 passed in 3.57s` (`test_providers.py`: 7 passed)

Unverified: live network calls, auth brokers, OAuth, retries, streaming, usage accounting, embeddings, images, and the model catalog.
