---
status: passed
---

# Verification 22: MCP SDK layer

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_mcp_session.py -q` → exit 0,
  6 passed (initialize + tools/call against a scripted stdio server via the
  real SDK, error shape with result, refusals spawn nothing, spawn error,
  timeout names the timeout and the child pid is reaped).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 141 passed (135 + 6).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- One-shot `mcp_call` untouched; no network in tests.

## Requirements

- MCP-01, MCP-02: Done.
