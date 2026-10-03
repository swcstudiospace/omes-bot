# Vendored behavior

Omes Bot does not vendor, subtree, or import either upstream checkout at runtime. Both trees sit in this working directory so a port can read them. `.gitignore` keeps them out of this repository. Behavior is reimplemented under `omes/` and this file records the commit the port was read from.

## Hermes Agent

- Remote: https://github.com/NousResearch/hermes-agent.git
- Commit: `1a4508e2aff2db5f50409893a2115be777bd5643`
- Modules adapted: `agent/conversation_loop.py`, `agent/turn_iteration_prep.py`, `agent/turn_tool_round.py`, `agent/turn_final_response.py`, `agent/turn_finalizer.py`, `agent/prompt_builder.py`, `agent/iteration_budget.py`, `agent/interrupt_control.py`, `agent/turn_facade_lease.py`, `agent/agent_runtime_helpers.py` (`apply_pending_steer_to_tool_results`), `agent/turn_preflight.py`, and `agent/conversation_compression.py` from commit `1a4508e2aff2db5f50409893a2115be777bd5643`.
- Tool modules adapted: `tools/registry.py`, `tools/file_operations.py`, `tools/patch_parser.py`, `tools/file_operations_search.py`, `tools/terminal_tool.py` (local argv backend only), `tools/todo_tool.py`, `tools/clarify_tool.py`, `tools/web_tools.py`, and `tools/vision_tools.py` from commit `1a4508e2aff2db5f50409893a2115be777bd5643`.
- Growth modules adapted: `tools/skill_manager_tool.py`, `tools/skills_tool.py`, `agent/skill_utils.py`, `tools/memory_tool.py`, `tools/memory_tool_store.py`, `agent/memory_provider.py`, `agent/memory_manager.py`, `tools/session_search_tool.py`, and `agent/curator.py` from commit `1a4508e2aff2db5f50409893a2115be777bd5643`.
- Delegation and cron tick adapted: `tools/delegate_tool.py` and `cron/scheduler_tick.py` from commit `1a4508e2aff2db5f50409893a2115be777bd5643`.
- Platform modules adapted: `tools/code_execution_tool.py`, `tools/mcp_tool.py`, `tools/browser_tool.py`, `tools/approval.py`, and plugin `register` (`hermes_cli/plugins.py` `register_tool`) from commit `1a4508e2aff2db5f50409893a2115be777bd5643`.
- License: MIT
- Copyright: Copyright (c) 2025 Nous Research
- What is adapted: the agent runtime. Conversation loop and turn phases, session, budget, interrupt, prompt builder, compression, tool registry and toolsets, skills and curator, memory and session search, delegation, cron, and plugin registration for tools, memory, and model providers.
- What is not adapted: TUI, desktop, website, UI locales, nix and docker packaging, messaging gateways, Feishu, Yuanbao, Home Assistant, Spotify, and the kanban UI. A later phase may pull a piece in only if that phase cannot pass its own tests without it.

## oh-my-pi (Omp)

- Remote: https://github.com/can1357/oh-my-pi.git
- Commit: `0e2411c0df59fce8c56dc03a5f1c9afffcb0d746`
- Harness modules adapted: `packages/agent/src/agent-loop.ts` (turn events, `beforeModelCall`), `packages/agent/src/live-steering.ts`, `packages/agent/src/pause.ts`, `packages/agent/src/output-budget.ts` (`fitOutputTokensToContextWindow`), `packages/agent/src/compaction/pruning.ts`, and `packages/agent/src/speculative-execution.ts` from commit `0e2411c0df59fce8c56dc03a5f1c9afffcb0d746`.
- License: MIT
- Copyright: Copyright Mario Zechner 2025, Can Bölük 2025-2026, Stencil Labs 2026
- What is adapted: `packages/agent` behavior, the coding-agent tool and edit pipeline, LSP, DAP, sessions, tasks, MCP, capabilities, extensions, modes and plan mode, memories, hindsight, mnemopi, autolearn, goals, advisor, exec job control, agent-side security, and the `packages/ai` provider surface. The port is Python inside the same Omes agent. TypeScript tests are the spec.
- What is not adapted: `packages/tui`, collab web, stats site, CLI gallery and install chrome, Rust crates, and bazel or nix packaging. Same exception as Hermes: pull a piece in only when a phase's tests cannot pass without it.

## Merge rule

One Python process. One `OmesAgent`. Where both upstreams implement the same concern, one Omes implementation has to satisfy both invariants. Temporal is not the merge. It can become a durability adapter after cron and delegation exist.
