# Phase 68 Plan: Slash commands and workflows

**Requirements:** GBX-01, GBX-03, GBX-05, GBX-06, GBX-07.

Own only these paths:

- `omega_prime/grokbot/commands.py`
- `omega_prime/grokbot/workflows.py`
- `omega_prime/grokbot/seeds/memory.txt`
- `omega_prime/tools/omega_command.py`
- `omega_prime/tests/test_omega_commands.py`

Do not edit `mcp_server.py`, the prompt, the template, the roster, or the agent loop. Another task wires those against the API below.

## API (do not rename)

```python
def parse_omega_command(text: str) -> tuple[str, str] | None:
    """Whole message only. `/omega-help` -> (`omega-help`, ``).
    `/omega-recall ships` -> (`omega-recall`, `ships`). None for prose.
    """

def execute_command(text: str, registry: Any, env: Mapping[str, str]) -> dict:
    """Stable JSON-ready dict. Never raises for a bad command."""

def register_omega_command_tools(registry: ToolRegistry, env: Mapping[str, str] | None = None) -> list[str]:
    """Registers `omega_command`. Returns `["omega_command"]`."""
```

`omega_command(command: str) -> str` returns `json.dumps(execute_command(...))`.

`parse_omega_command` strips the message, lowercases the name, and matches only `^/omega-([a-z0-9]+)(?:\s+(\S[\s\S]*))?$` after strip. A mention inside a sentence is `None`.

## Commands

| Name | Args | Behavior |
|---|---|---|
| `omega-help` | no | Catalog: `name`, `usage`, `summary`, `when` for every command |
| `omega-doctor` | no | `registry.dispatch("lead_doctor", {"action": "check"})` |
| `omega-roster` | no | `registry.dispatch("lead_roster_status", {})` |
| `omega-recall` | query required | `registry.dispatch("lead_memory_recall", {"query": args})` |
| `omega-retain` | text required | Refuse secrets first (no dispatch). Else `memory` `action=add`, `target=memory`, content prefixed with `[hindsight:omega-prime-lead] ` when that prefix is absent |
| `omega-gates` | no | `registry.dispatch("qua_gates_run", {})` |
| `omega-python` | no | workflow `python-clean` |
| `omega-delegate` | goal required | `registry.dispatch("delegate_task", {"goal": args})` |
| `omega-workflow` | name required | `run_workflow` |
| `omega-onboard` | no | workflow `onboard` |
| `omega-connectors` | no | `connector_requests(env)` |
| `omega-desk` | no | workflow `desk` |

Unknown name: `ok: false`, `error: "unknown_command"`, and the command names. Missing args: `error: "missing_args"` plus `usage`. Not a command: `error: "not_a_command"`.

Every success and failure is `{ok, command, ...}`. Tool JSON is parsed. A tool `error` makes that step `ok: false` and is returned as `result`, not replaced with a fake success. `execute_command` itself does not raise if dispatch returns an error JSON. If dispatch raises, catch it and return `ok: false`, `error: "dispatch_failed"`, `reason` the exception type and message.

Secret refusal (no tool call) if the text matches `(?i)(api[_-]?key|token|secret|password|private[_-]?key)\s*[:=]\s*\S+`, contains `BEGIN PRIVATE KEY`, or starts with `sk-`. `error: "secret_refused"`. The reason says not to put a secret in chat or memory. Do not echo the secret back.

## Workflows

`run_workflow(name, registry, env) -> dict` with `workflow`, `ok`, `steps`. Unknown name: `ok: false`, `error: "unknown_workflow"`, `workflows` listing the four names.

- `python-clean`: `run_terminal` argv `[sys.executable, "-m", "ruff", "check", "."]` timeout 120, then `[sys.executable, "-m", "compileall", "-q", "."]` timeout 120. `stop_on_error` true. A step with `error`, or `exit_code` other than 0, stops the workflow and sets `ok` false.
- `onboard`: `lead_doctor` `{action: check}`, `lead_roster_status` `{}`, then seed, then connector requests. `stop_on_error` false. `ok` is true when every step ran (an approval error or `not_configured` is recorded, not fatal).
- `desk`: `lead_doctor` check, `lead_roster_status`, `lead_intake_next` `{}`. `stop_on_error` false. Same `ok` rule as onboard.
- `connectors`: only `connector_requests`.

`connector_requests(env)` returns `{configured: [{id, env}], requests: [{id, env, ask}]}`. Blank or missing counts as absent. Never copy env values into the result.

| id | present when | ask (no secret, say "do not paste it into chat") |
|---|---|---|
| x | `X_API_TOKEN` | X connector |
| telegram | `TELEGRAM_BOT_TOKEN` | Telegram connector |
| discord | `DISCORD_BOT_TOKEN` | Discord connector |
| delegate | any of `XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | child model for `/omega-delegate` |
| substrate | any of `SUBSTRATE_TOKEN`, `SUBSTRATE_TOKEN_GROK_BOT` | substrate brief and events |
| hindsight | any of `HINDSIGHT_API_KEY`, `HINDSIGHT_API_TOKEN` | shared episodic bank |
| railway | `RAILWAY_TOKEN` | Railway status and logs |
| greptile | `GREPTILE_API_KEY` | Greptile review |
| vercel | `VERCEL_TOKEN` | Vercel deployments |
| play | `PLAY_CONSOLE_TOKEN` | Play Console |
| appstore | all of `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_PRIVATE_KEY` | App Store Connect |

## Seed

Read `omega_prime/grokbot/seeds/memory.txt` (UTF-8, no `§`, under 1800 characters). `seed_memory(registry)` dispatches `memory` add of `[hindsight:omega-prime-lead] ` plus the file text when the prefix is not already in the file. The file text states: one bot `bot-00-omega-prime`; a message that is only `/omega-...` is run with the `omega_command` tool; `/omega-help` lists commands; `/omega-onboard` is first run; `/omega-python` is ruff and compileall; connector tokens are host env, never chat.

## Tool schema

Description tells the model: pass the user's `/omega-...` text; use this instead of the underlying tools for a slash command or for onboard, connectors, a Python check, desk status, doctor, roster, recall, retain, gates, or delegate. One string argument `command`, required.

## Tests (fake registry, no network, no pytest-of-the-suite)

- prose `please /omega-help` parses as `None`; `/omega-help` and `/omega-recall ships` parse
- help lists all 12 names
- unknown command lists names and does not call dispatch
- retain of `X_API_TOKEN=abc` does not call dispatch
- retain of ordinary text calls `memory` with the hindsight prefix
- connectors with `X_API_TOKEN` set lists `x` configured and does not contain the token value; telegram is a request
- python-clean records the two argv lists and stops after a non-zero ruff exit
- onboard runs doctor, roster, seed, and connectors even when doctor returns `{"error": "approval required"}`
- second seed add is still dispatched (the store's duplicate rule is not reimplemented here)
- `register_omega_command_tools` serves `omega_command`, and dispatching it runs help

Match nearby SPDX headers. Skip pytest, ruff, mypy, and formatters.
