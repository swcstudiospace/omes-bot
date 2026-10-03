---
phase: 06-remaining-hermes-tools
plan: 01
subsystem: tools
tags: [execute, mcp, browser, approvals, plugins]
provides:
  - Local code execution, MCP client, browser tools, approval gate, and plugin registration
affects: [07-omp-harness]
---

# Phase 6 summary

`execute_code` writes the snippet to a file inside the temp home and runs `[sys.executable, that_file]` with `cwd=home`, `shell=False`, and a timeout; empty code returns an error and starts nothing. `mcp_call` spawns an argv command (a string command is an error), writes one JSON-RPC `tools/call` line to stdin, and returns the one JSON line from stdout as `result`. `BrowserSession` wraps an injected transport: `browser_navigate` records the URL and returns `url` plus `page`, `browser_snapshot` returns `page`; no socket is opened. `ApprovalLog.approve` records only when `approved_by` is non-empty and not the bot id; `dispatch` returns `approval required` without calling the handler when a flagged tool is unapproved. `load_plugins` loads each `{home}/plugins/<name>/plugin.py` with a safe name whose resolved path stays inside `home`, calls `register(registry)`, and returns the registered names. `register_platform_tools` registers `execute_code`, `mcp_call`, `browser_navigate`, and `browser_snapshot` bound to the home and browser.

The roster lists the coding tools, then the four growth tools, then `delegate_task`, then the four platform names.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `47 passed in 2.33s` (`test_platform.py`: 6 passed)

Unverified: no persistent kernel, remote sandboxes, MCP SDK, gateway approval queues, or live browser process.
