# Summary 41-01: Loop events + docs_search tool

## What was built

- `SubstrateClient.docs_search` (MCP `tools/call`, truthful errors).
- `omes/substrate/session.py`: `SubstrateSession` — idempotent `open()`
  (session.start + brief + `.substrate/BRIEF.md`), `on_prompt` (redacted,
  truncated), `on_tool_call` (name-only + `file.edit` for edit tools),
  `on_turn_end` note, idempotent `close()`; every method fail-open, args
  never leave the process.
- Loop wiring: `Agent.substrate` field; `run_conversation` opens, injects
  the brief block, reports prompt + turn-end; `run_tool_round` reports each
  call. All hooks never raise; `None` keeps turns fully local.
- `omes/tools/substrate_tools.py`: `substrate_docs_search` family +
  `SUBSTRATE_TOOL_NAMES`, roster/policy/test-exactness updates, and
  `default_registry` wiring (`SUBSTRATE_URL`/`SUBSTRATE_TOKEN*` env).
- Explicit `token` param on `SubstrateClient` (mirrors connector clients;
  wins over broker, redacted in failures).

## Verification

`.venv/bin/python -m pytest omes/tests -q` → exit 0, 281 passed
(270 carried + 11 new). No network in tests. No new dependencies.
