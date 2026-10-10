---
status: complete
requirements_completed: [GBX-02, GBX-04, GBX-08]
---

# Phase 69 Summary: Grok surface

**Requirements:** GBX-02, GBX-04, GBX-08. All wired.

`omega_command` is registered immediately after `delegate_task` and listed in that slot on the roster, the seat policy, and the assembled prompt. The default host serves 110 tools (147 on the roster). Prime families stay off. The tool description tells the model to pass the user's `/omega-...` text and to use this tool for onboard, connectors, a Python check, desk status, doctor, roster, recall, retain, gates, or delegate.

`OmegaPrimeAgent.run` intercepts a message that is only a slash command when the tool is registered. It dispatches `omega_command`, records the user and assistant rows, takes and releases the session lease, and does not call the model. Prose that mentions `/omega-help` still goes to the model.

The template enables skill `omega-commands` and names routines `onboard`, `python-clean`, and `connectors`. Those three files live under `routines/` and point at the slash command. First run is `/omega-onboard`. The desk-bootstrap adaptation no longer sends this bot through `/desk bootstrap` as its first run.

Docs that stated a served count of 109 now state 110 (138 with the five config-gated families that the host can serve). The seat policy allow list matches the 147-name roster, including `omega_command`.
