# Omes Bot setup

Four steps: install, secrets, optional tool host, smoke prompt.
Takes about ten minutes; only step 3 needs a machine of yours.

## 1. Install from the template

Open the Omes share link in Grok and choose **Add to Grok Bot**.
This creates an independent copy on your account — your chats,
secrets, and settings stay yours.

What the template carries: the Omes instructions, skills,
routines, and first-party plugins. What it never carries:
secrets, custom MCP servers, scripts, or private skills. Steps
2–3 re-add the ones you want.

## 2. Secrets

Omes never asks for secrets in chat. Add each value where the
connector asks for it (Grok Bot settings or your host's env):

| Secret | Needed for | Where it goes |
| --- | --- | --- |
| `XAI_API_KEY` | Grok model calls outside Grok Bot | host env, resolved via the credential broker |
| X API Bearer [REDACTED] | X connector tools | provided when wiring the connector |
| Telegram bot token (BotFather) | Telegram connector tools | provided when wiring the connector |
| Discord bot token | Discord connector tools | provided when wiring the connector |
| GitHub token | Greptile reviews, ship PRs | host via `gh auth` |

Skip what you don't use: every unconfigured client reports
`not_configured` instead of failing.

## 3. Optional: attach the tool host

Without this step Omes still answers from its prompt, skills, and
routines. With it, the bot also calls the real Omes tools.

On a machine you control (Linux, Mac, or WSL2):

```bash
git clone https://github.com/swcstudiospace/omes-bot.git
cd omes-bot
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m omes.mcp_server --root .
```

Then add it as a **custom MCP** server in your Grok Bot's settings,
pointing at that command. Prefer a sandbox: see
`omes/hosting/openshell/sandbox-policy.yaml`. Rivet AgentOS notes:
`omes/hosting/agentos/NOTES.md`.

## 4. Smoke prompt

Send the bot exactly this:

> `ultrathink` what tools do you have, and which need approval?

Expect back:

1. A short plan of how it will answer (the ultrathink notice fired).
2. A tool list matching `contracts/tool-rosters/omes.yaml` — with
   the tool host attached; without it, the bot says which tools
   live behind the host instead of inventing results.
3. The approval-gated tools named as needing approval.
4. No secrets, ids, or tokens quoted back.

If any line is missing, re-check the step above it. Builders can
also run the local verification:

```bash
.venv/bin/python -m omes.setup_check --root .
```
