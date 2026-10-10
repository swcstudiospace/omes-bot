---
name: omega-commands
description: When to call omega_command. A user message that is only /omega-... runs that slash command instead of the underlying tools.
bots: [bot-00-omega-prime]
---

# Omega commands

## L1 — Summary

Grok Bot reaches Omega Prime's sequences through one tool, `omega_command`.
Pass the slash text. Do not reimplement the sequence by calling the
underlying tools yourself.

**Decision tree:**

```
User message is only /omega-... ?
├─▶ Call omega_command with that exact text. Stop.
│
User asks to onboard, set up, or take a first run?
├─▶ /omega-onboard
│
User asks which connectors are missing?
├─▶ /omega-connectors. Never ask them to paste a token.
│
User asks whether the Python package is clean?
├─▶ /omega-python (ruff and compileall). Full suites are /omega-gates.
│
User asks for desk status?
├─▶ /omega-desk. Doctor alone is /omega-doctor.
│
User asks what the bot can run?
└─▶ /omega-help
```

## L2 — Do not

- Do not paste or request an API token, key, or private key in chat.
- Do not call `lead_doctor`, `lead_roster_status`, `memory`, or
  `run_terminal` yourself to imitate `/omega-onboard` or `/omega-python`.
- Do not treat a sentence that merely mentions `/omega-help` as the command.
  Prose goes to you; the bare slash message goes to `omega_command`.
