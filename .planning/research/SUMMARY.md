# Project Research Summary: v9 SOTA upgrade

**Date:** 2026-10-07
**Mode:** Inline (GSD research agents unavailable in this runtime)

## Key Findings

- **Stack additions:** Ruff (pinned, `[tool.ruff]`), a pip-installable
  typechecker (mypy or pyrefly — no Node), raised dep floors + lockfile, CI
  matrix through 3.14. No uv, no pyright, no ty-beta.
- **Feature table stakes:** lint/format + types in CI, retries + usage
  accounting in providers, hermetic tests (PyRIT isolation), Responses mode
  for OpenAI, guarded discord import for 3.13+.
- **Architecture:** all integration points are in-place (CI, pyproject,
  providers/, evals/); no new processes or packages; build order runs
  land → hygiene → providers → depth → evals/docs.
- **Watch Out For:** ruff drift (pin exactly), checker churn (fix to zero in
  one phase), audioop on 3.13+, PyRIT home writes, Responses fallback.

## Implications for Roadmap

- Phase 46 lands the dirty tree first (nothing else touches those files until
  it is verified and committed).
- One hygiene phase can carry ruff + types + pins + matrix (mechanical, big).
- Provider work splits naturally: resilience (retry/usage) → protocol
  (Responses/streaming) → depth (PyRIT orchestrators, chunk extraction).
- Requirements stay hermetic; every phase keeps suite + evals + assemble green.

## Sources

- Web: MCP spec/SDK v2 changelogs, xAI model catalogs, Anthropic/OpenAI API
  docs and SDKs, Ruff 0.16.x configs, Python 3.14/3.15 status, PyRIT 1.1.0,
  2026 typechecker comparisons, Responses-vs-Chat-Completions migration notes.
- Codebase: `omega_prime/providers/`, `omega_prime/mcp_server.py`, `omega_prime/evals/`,
  `omega_prime/tools/discord.py`, `pyproject.toml`, `.github/workflows/ci.yml`.
