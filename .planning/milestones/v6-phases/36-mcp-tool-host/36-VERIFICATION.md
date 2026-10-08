---
status: passed
---

# Verification 36: MCP tool host

## Checks (all observed this session)

- `.venv/bin/python -m pytest omega_prime/tests/test_mcp_server.py -q` → exit 0, 4 passed
  (list/call handlers + roster gate, default registry coverage, stdio dogfood).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 231 passed (227 + 4).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.

## Requirements

- MCP-01, MCP-02: Done.
