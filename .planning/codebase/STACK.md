# Stack: programming-desk (source) + Omes Bot (target)

## Source: programming-desk (107M on disk)

- `services/desk-gateway/` — Python MCP service (uv, `pyproject.toml`, `uv.lock`).
  Per-seat MCP servers (`SeatServer(MCPServer)`, one `/mcp/<seat>` endpoint),
  61 async tools in `tools/{core,lead,web,mobile,systems,infra,quality,packs}.py`,
  `upstreams.py` (14 upstream clients), `server.py` (ASGI app + bearer auth),
  `store.py`, `live.py`, `oauth.py`, `rosters.py`, `config.py`, `repo.py`,
  `audit.py`, `redact.py`, `schema.py`. Tests in `tests/`.
- `web/desk3d/` — TypeScript 3D desk UI (37M `node_modules`, 2.2M `dist`).
  Product chrome; out of scope for the Omes port by precedent.
- `web/mcp-unified-lsp/` (56K) — LSP helper; check before porting LSP-adjacent work.
- `prompts/` — per-seat XML (`bot-00`..`bot-06` + `LEAD|SYSTEMS|WEB|ANDROID|IOS|INFRA|QUALITY.xml`)
  plus `prompts/_shared/core-directives.xml`; `prompts-assembled/` is generated.
- `contracts/` — YAML rosters per seat (`_core.yaml` + 7 seats), tool-packs
  (`clippyos`, `desklanes`, `kanbanos`), `events/desk-live-v1.md`, `changes/`.
- `skills/` — 13 `SKILL.md` skills + `platforms/` (8 stacks) + `security/` (2).
- `ci/gates/` — 7 Python gate scripts (`run_all.py` + 6 checks).
- `infra/`, `scripts/`, `docs/`, `grokbot/` (templates + roster JSON + avatars),
  `ownership.yaml`, `vendor/ultrathink-policy`.

## Target: Omes Bot (this repo)

- One Python process (`omes/`), stdlib-first core, pytest suite (`omes/tests`),
  data-driven evals (`omes/evals/cases/*.json` + `runner.py`).
- v4 pip deps: tweepy, mcp, pyrit, apscheduler, aiogram, discord.py.
- Registry tools + YAML roster + JSON seat policy + credential broker;
  `receipts.py` (verification receipts), `ownership.yaml`, skills runtime,
  routines, Grok template + assembled prompt.
- Vision/browser are injected-transport shells (`vision_analyze`,
  `BrowserSession.navigate/snapshot`) with no live backend yet.
