---
phase: 47-lint-types
plan: "01"
subsystem: testing
tags: [ruff, mypy, ci]
requirements-completed: [HYG-01, HYG-02, HYG-03]
completed: 2026-10-07
status: complete
---

# Summary 47-01: Ruff + mypy clean and CI-enforced

**Enforced clean Ruff formatting/lint and mypy checks in CI.**

## What was built

- `pyproject.toml`: `[tool.ruff]` (py311, 88 cols, E4/E7/E9/F/I/UP/B/SIM/RUF,
  E501 to formatter, omega_prime first-party), `[tool.mypy]` (py311,
  check_untyped_defs, ignore_missing_imports), `dev` extra pinning
  `ruff==0.16.10`, `mypy==2.4.0`.
- 138 files: ruff --fix + format (119 files), then hand fixes to zero —
  SIM105→suppress, B023 default-arg bind, zip strict, escaped raises
  patterns, SIM102/SIM117 merges.
- mypy 153→0 over 173 files: declared Agent fields (delegate depth, child
  model/hook, prompt cache, turn budget), annotated handler dicts (15
  files), narrowing asserts in tests, `Literal[False]` lease exit, honest
  fake/signature types (tick runner Any, FakeTransport 4-tuples, opener
  callable, HTTPError Message), canonical MCP kwargs, 7 targeted
  `type: ignore`s (5 intentional-misuse tests, 1 lookup-less client,
  1 moved ignore). No runtime behavior changes.
- CI: `lint` job (ruff check + format --check) and `types` job (mypy),
  both installing `.[dev]`.
- `omega_prime/tests/test_lint_types.py`: 5 gate tests (ruff/mypy config, exact
  pins, CI jobs, canonical MCP spellings).

## Verification

`ruff check omega_prime/` → clean. `ruff format --check` → clean (204 files).
`mypy omega_prime/` → 0 errors, 173 files. Suite → exit 0, 315 passed
(310 carried + 5 new). Evals → 23 passed. Assemble --check → exit 0.
setup_check → ok. Commit `0fa783f`.
