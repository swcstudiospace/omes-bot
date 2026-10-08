---
phase: 48-deps-matrix
plan: "01"
subsystem: infra
tags: [dependencies, python, mcp]
requirements-completed: [HYG-04, HYG-05, HYG-06]
completed: 2026-10-07
status: complete
---

# Summary 48-01: Floors, lockfile, matrix, discord guard, MCP pin

**Pinned dependency floors and added the Python matrix with a Discord import guard.**

## What was built

- Floors at verified versions (mcp capped `<3`); 3.13/3.14 classifiers.
- `requirements-lock.txt`: 146-pin freeze + header; setup docs mention it.
- CI `verify`/`lint`/`types` run the 3.12/3.13/3.14 matrix (docs stays 3.12).
- Discord guard: try/except import in tools + tests; fail-soft factory
  raising DiscordError; library-failure test decoupled from discord.py;
  real-client test skips when unimportable.
- MCP 2026-07-28 conformance note in `docs/tool-host.md`.
- `omes/tests/test_deps_matrix.py`: 5 gate tests (floors, installed,
  lockfile, matrix, subprocess import-guard proof). +1 discord branch test.

## Verification

Suite → exit 0, 321 passed (315 + 6 new). Evals → 23 passed. Assemble,
ruff, mypy, setup_check green. Faithful 3.13 simulation (audioop blocked
via meta-path probe in /tmp): 315 passed + 1 skip — only the real-client
test skips; collection and all other tests pass. Real 3.13/3.14 runs
happen in CI (no local interpreters). Commit `ca48e4d`.
