---
status: complete
requirements_completed: [BND-05, BND-06]
---

# Phase 72 Summary: Family reachability

**Requirements:** BND-05, BND-06. Both wired. The served counts in the original requirement text (110 off, 147 on) were the pre-phase-73 baseline. Phase 73 added seven always-on tools, so the final numbers are 117 and 154. The notes on `REQUIREMENTS.md` required that update in the same milestone.

`default_registry` registers `rlm` when `prime.rlm.enabled` is on. The parent is `_RlmParent`, the desk parent plus `session_dir` and session name `bot-00-omega-prime`. Without a child-model provider, `rlm_spawn` and `rlm_create_session` return `not_configured: provider`. The seven names are `rlm_spawn`, `rlm_collect`, `rlm_list_subagents`, `rlm_delete_subagent`, `rlm_create_session`, `rlm_progress_note`, `rlm_rename`.

`default_registry` registers `messaging` when `prime.messaging.enabled` is on, on session `bot-00-omega-prime`. The names are `agent_message_send` and `agent_observe`.

Flags off: neither family is in the served set. With all seven Prime flags on, the served set equals the roster set (154 names). `README.md`, `docs/agent-loop.md`, `docs/driving-the-bot.md`, and `docs/tool-host.md` say how to turn each family on. They no longer say the host refuses to register `rlm` or `messaging`.
