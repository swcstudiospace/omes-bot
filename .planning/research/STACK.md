# Stack Research: v9 SOTA upgrade

**Date:** 2026-10-07
**Mode:** Inline (GSD research agents unavailable in this runtime)

## Current landscape (verified 2026-10-07)

| Piece | Omega Prime today | SOTA (Oct 2026) | Action |
|---|---|---|---|
| Python | `>=3.11`, CI on 3.12 | 3.14.8 stable; 3.15 RC; 3.10 EOL Oct 2026; 3.11 security-only to Oct 2027 | CI matrix incl. 3.13/3.14; keep floor 3.11 |
| Linter/formatter | none | Ruff 0.16.9 is the standard (`ruff check` + `ruff format`, config in pyproject) | Add `[tool.ruff]`, pin exact in dev extra, CI job |
| Typechecker | none | pyright (default, needs Node), mypy (mature, pure pip), pyrefly 1.0 (Rust, pip wheel), ty beta | pip-installable checker in CI (no Node per repo constraint) |
| MCP SDK | `mcp>=1.0`, installed 2.3.0 | v2 stable (spec 2026-07-28); v1 maintenance-only | Pin `mcp>=2,<3`; verify no v1-isms (none found: no FastMCP use) |
| PyRIT | `pyrit>=1.0`, installed 1.1.0 | 1.1.0 current (Sep 2026); repo moved Azure→microsoft | Keep; fix home-dir writes in tests |
| tweepy/aiogram/discord.py/playwright/APScheduler/Appium | floors below installed | installed (4.17/3.31/2.7.1/1.63/3.11.3/6.0.7) are current | Raise `>=` floors to verified versions; add lockfile |
| xAI/Grok | chat_completions at api.x.ai/v1 | Still correct; current models grok-4.5/4.6/4.7 | Refresh documented defaults; no wire change |
| OpenAI | chat_completions only | Responses API is default/recommended; chat_completions for compatibles | Add Responses mode for api.openai.com |
| Anthropic | header 2023-06-01, max 4096 | Header still valid; 4096 max is low | Keep header; raise default max_tokens |
| discord.py + 3.13 | top-level `import discord` | audioop removed in 3.13 → import breaks | Lazy/guard import (Omega Prime is REST-only) |

## What NOT to add

- **uv**: new global toolchain, violates repo constraint. pip + lockfile instead.
- **pyright**: needs Node; violates "no new global toolchain". mypy or pyrefly (pip wheel) instead.
- **ty**: still beta (0.0.x); revisit at 1.0.
- **Live API lanes in CI**: user chose hermetic + opt-in (2026-10-07).
