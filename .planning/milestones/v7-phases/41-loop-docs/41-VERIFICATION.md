# Verification: Phase 41 Loop wiring + docs

**Status:** passed
**Date:** 2026-10-03

## Success criteria

1. Sessions open with a brief injected (BRIEF.md fallback) and emit
   session/prompt/tool/file/session-end events with surface + graph_id
   provenance — PASS (session + ScriptedModel loop-integration tests).
2. A docs_search tool returns RAGflow citations via substrate MCP, or a clear
   error when the plane is unconfigured — PASS (registry dispatch tests;
   retrieval passthrough, plane error, unreachable error).

## Commands

- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 281 passed.
- `.venv/bin/python -m pytest omes/tests/test_substrate_session.py -q` → exit 0, 9 passed.

## Requirements

- SUB-03: Done. RAG-01: Done.
