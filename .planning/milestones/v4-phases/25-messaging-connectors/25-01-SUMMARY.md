# Summary 25-01: Telegram and Discord connectors and dependencies

## What shipped

`omega_prime/tools/telegram.py`: `TelegramClient` on aiogram (`get_updates`,
`send_message`), `TELEGRAM_TOOL_NAMES = (telegram_updates, telegram_send)`,
brokered `TELEGRAM_BOT_TOKEN` per `https://api.telegram.org`, approval on
sends, plain-dict results, `TelegramError` naming the operation.

`omega_prime/tools/discord.py`: `DiscordClient` on discord.py REST-only (per call:
`login` + `fetch_channel` + `history`/`send` + `close`; no gateway),
`DISCORD_TOOL_NAMES = (discord_read, discord_send)`, brokered
`DISCORD_BOT_TOKEN` per `https://discord.com`, approval on sends,
`DiscordError` mirroring the Telegram contract.

Both are sync façades over async libraries: each method creates the peer,
runs the call, and closes it inside one `asyncio.run`, so loop-bound
sessions never escape. Both follow the Phase 17 shape (client,
`with_broker`, `register_*_tools` with drift guard, `ValueError` for bad
arguments surfaced as tool `error` dicts).

Consistency: `omega-prime.yaml` roster gains the four names after the X family;
`omega-prime.json` shipped policy allow-lists them (network hosts stay empty per
the v2 deny-by-default decision); the roster-composition assertions in
`test_tools.py`, `test_growth.py`, and `test_providers.py` register and
expect the new families.

`pyproject.toml` gains `aiogram>=3.0` and `discord.py>=2.0` (verified
against 3.31.0 / 2.7.1). CI already installs the project.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_telegram.py
  omega_prime/tests/test_discord.py -q` → exit 0, 17 passed (shape mapping, reply
  threading, argument validation, broker flow and pre-call refusal, approval
  gating, real peer construction without network).
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 167 passed (150 + 17).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.

## Follow-ups

- Long-poll / gateway listeners for live inbound handling (today: polling
  reads on demand).
- OAuth2 user-context for Discord where bot tokens are insufficient.
- Gateway intents review if presence/message-content reads are ever needed.
