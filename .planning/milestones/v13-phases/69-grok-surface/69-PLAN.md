# Phase 69 Plan: Grok surface

**Requirements:** GBX-02, GBX-04, GBX-08.

The engine is created in parallel by phase 68. Import it; do not reimplement it. If a file is missing while you edit, still write the call sites exactly as specified.

API to call:

```python
from omega_prime.tools.omega_command import register_omega_command_tools
# register_omega_command_tools(registry, env) -> ["omega_command"]
```

`parse_omega_command` lives in `omega_prime.grokbot.commands`.

## Own only

- `omega_prime/mcp_server.py` — one import and one `register_omega_command_tools(registry, env)` call immediately after `register_delegate_tools`
- `omega_prime/agent/runtime.py` — `OmegaPrimeAgent.run` intercept
- `omega_prime/contracts/tool-rosters/omega-prime.yaml` — insert `omega_command` immediately after `delegate_task`, and one comment line that it comes from `register_omega_command_tools`
- `omega_prime/prompts/bot-00-omega-prime.xml` — `<tool name="omega_command"/>` in that same slot; a `<skill>` for `skills/omega-commands/SKILL.md` with `load="always"`; three `<routine>` entries
- `omega_prime/grokbot/templates/OMEGA_PRIME.md` — enable skill `omega-commands`; add routines `onboard`, `python-clean`, `connectors`; first-run sentence names `/omega-onboard`
- `omega_prime/routines/onboard.md`, `python-clean.md`, `connectors.md`
- `omega_prime/skills/omega-commands/SKILL.md`
- `omega_prime/skills/desk-bootstrap/SKILL.md` — only the "Omega Prime adaptation" section
- `README.md` — the sentence that says the served count is 109: say the count is whatever `setup_check` reports (110 after this tool; Prime families stay off)
- `omega_prime/tests/test_omega_surface.py`

Do not edit `prompts-assembled/`, `docs/tool-catalog.md`, `commands.py`, or `workflows.py`. Do not start `DeskDriver`.

## Loop intercept

In `OmegaPrimeAgent.run`, before `run_conversation`: if `user_message` is a `str` and `parse_omega_command` returns a pair and `"omega_command"` is a registered tool, dispatch `omega_command` with `{"command": user_message.strip()}` on `self.registry`. Append the user row and an assistant row whose content is the dispatch string. Return `{"final_response": <that string>, "messages": self.messages, "api_call_count": 0, "turn_exit_reason": "omega_command"}`. Do not call the model. Take and release `self.lease` the same way `run_conversation` does (`acquire(wait=wait)` / `release` in `finally`). Any other message, including prose that merely mentions `/omega-help`, goes through `run_conversation` unchanged.

## Copy

Skill `omega-commands` (frontmatter `name: omega-commands`, bots `[bot-00-omega-prime]`):

- A user message that is only `/omega-...` → call `omega_command` with that exact text. Do not call the underlying tools yourself.
- Onboard, "what's missing", or first run → `/omega-onboard`.
- Connector setup → `/omega-connectors`. Never ask the user to paste a token.
- Python cleanliness → `/omega-python` (ruff + compileall). Full suites → `/omega-gates`.
- Desk status → `/omega-desk`. Doctor alone → `/omega-doctor`.
- `/omega-help` lists the catalog.

Routines are three short markdown files, same shape as `omega_prime/routines/sweep.md`: name the slash command and say the file points at `omega_prime.grokbot.commands` and does not copy the procedure.

Desk-bootstrap adaptation: first run is `/omega-onboard` via `omega_command`, then `grokbot/SETUP.md`. The `/desk bootstrap` procedure below is the old seven-seat gateway flow, not this bot's first run.

Template description: first run is the slash command `/omega-onboard`. Keep the existing paused note on `desk-lead`.

Prompt routine entries name `routines/onboard.md`, `routines/python-clean.md`, `routines/connectors.md`.

## Tests

`test_omega_surface.py`:

- `default_registry` with `OMEGA_PRIME_STATE_DIR` pointed at `tmp_path` serves `omega_command`. `/omega-help` via dispatch lists `omega-onboard` and does not call a model.
- `/omega-onboard` records a doctor error or a doctor body, and a later `/omega-recall slash` (or the seed's distinctive phrase) sees the seed through `lead_memory_recall`. Approve nothing unless the test fails closed; the seed step must run even when doctor returns an approval error. Do not write `omega_prime/memory/MEMORY.md` in the repo.
- `OmegaPrimeAgent` with a model whose `complete` raises `AssertionError`, and a registry that has `omega_command`, runs `/omega-help` without calling `complete`. A prose message `please /omega-help` does call `complete` (stub it to return a final text response with no tool calls — look at `ScriptedModel` in `omega_prime/agent/model.py`).
- Template file contains `omega-commands`, `onboard`, `python-clean`, and `connectors`. Roster yaml lists `omega_command` after `delegate_task`.

Skip pytest, ruff, mypy, and formatters.
