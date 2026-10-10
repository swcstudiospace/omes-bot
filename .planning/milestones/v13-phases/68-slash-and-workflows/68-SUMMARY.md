---
status: complete
requirements_completed: [GBX-01, GBX-03, GBX-05, GBX-06, GBX-07]
---

# Phase 68 Summary: Slash commands and workflows

**Requirements:** GBX-01, GBX-03, GBX-05, GBX-06, GBX-07. All wired.

A user message that is only `/omega-<name>` is a command. `parse_omega_command` accepts that shape, lowercases the name, and returns `None` for prose that merely mentions a command. `execute_command` runs the twelve-name catalog and returns `{ok, command, ...}`. Unknown names, missing args, and a message that is not a command are errors. A retain that looks like a secret is refused before any tool call and the secret is not echoed.

Workflows `onboard`, `python-clean`, `connectors`, and `desk` dispatch a fixed step list. `python-clean` runs `ruff check` then `compileall` through `run_terminal` argv and stops on a non-zero exit or a tool error. `onboard` and `desk` record a step error and still run the later steps. No step replaces an error with a success.

`onboard` seeds `omega_prime/grokbot/seeds/memory.txt` (465 bytes, no `§`, no secret) through the `memory` tool, tagged `[hindsight:omega-prime-lead]`. The seed names the slash commands and says connector tokens stay in host env.

`/omega-connectors` lists configured connector ids and a request for each missing one. A set token is never copied into the result. Blank values count as missing. `/omega-python` is the short check. `/omega-gates` dispatches `qua_gates_run`.
