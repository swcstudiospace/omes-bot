# Architecture Research: v9 SOTA upgrade

**Date:** 2026-10-07
**Mode:** Inline (GSD research agents unavailable in this runtime)

## Integration points

- **CI** (`.github/workflows/ci.yml`): add lint job (ruff), typecheck job
  (pip-installable checker), extend Python matrix to 3.13/3.14.
- **pyproject.toml**: `[tool.ruff]` config, dev extras with exact pins
  (ruff; checker), raised `>=` floors, 3.13/3.14 classifiers.
- **Lockfile**: committed `requirements-lock.txt` (pip freeze, no new toolchain).
- **Providers** (`omes/providers/`): retry + usage in `ProviderModel`;
  Responses mode in `openai.py`; streaming as a new `Transport` method so
  `FakeTransport` keeps tests hermetic; raised Anthropic `max_tokens`.
- **Discord import** (`omes/tools/discord.py` + test): lazy/guard so 3.13/3.14
  (no audioop) import cleanly; Omes uses REST only.
- **PyRIT target** (`omes/evals/pyrit_target.py` + test): isolate HOME/data dir
  per test so collection never touches `~/.local/share`.
- **Evals** (`omes/evals/`): orchestrator + scorer cases (deterministic subset);
  chunk extraction in substrate docs_search.

## New vs modified

- New: CI jobs, lockfile, Responses request builder, streaming transport method,
  eval cases. Modified: provider base, discord import, pyrit test isolation,
  docs defaults. No new packages, no new processes, no architecture change.

## Suggested build order

1. Land in-flight tree hardening (verify + commit).
2. Hygiene (ruff → types → pins/lockfile → matrix).
3. Provider currency (retries/usage → Responses → streaming).
4. Depth (PyRIT orchestrators/scorers, chunk extraction, deferred wins).
5. Eval battery growth + docs refresh.
