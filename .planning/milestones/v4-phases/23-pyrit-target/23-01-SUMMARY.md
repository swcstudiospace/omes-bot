# Summary 23-01: PyRIT target adapter and battery

## What shipped

`omega_prime/evals/pyrit_target.py`: `OmegaPrimePromptTarget` (a PyRIT `PromptTarget`
wrapping a sync `respond(text)` callable), `registry_responder` (parses
`{"tool", "arguments"}` and returns `registry.dispatch` verbatim; anything
else is a JSON error that dispatches nothing), `message_text`, and
`run_battery` driving `send_prompt_async` per prompt. Memory is in-memory
silent SQLite via an idempotent `ensure_memory()` — no keys, no files.

`omega_prime/evals/cases/adversarial.json`: five battery cases (unapproved publish,
policy-forbidden tool, unknown tool, raw injection, malformed JSON) with
structural contains/not-contains assertions.

`pyproject.toml` gains `pyrit>=1.0` (verified against 1.1.0). CI already
installs the project, so no workflow change.

Notes from the real SDK: 1.1.0 uses the message API (`Message.from_prompt`,
`send_prompt_async(message=)`), requires `CentralMemory` (SQLite-backed,
no DuckDB), and enforces keyword-only target `__init__` params.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_pyrit_target.py -q` → exit 0,
  3 passed (battery refusals through the real send path with an empty canary
  log, approved-control payload, assistant message shape).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 144 passed (141 + 3).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.

## Follow-ups

- Drive the target with a real PyRIT orchestrator (multi-turn Crescendo)
  once a model-backed `respond` exists.
- Score battery runs with PyRIT scorers instead of substring assertions.
