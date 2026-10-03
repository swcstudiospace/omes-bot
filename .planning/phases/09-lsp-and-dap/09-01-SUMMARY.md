---
phase: 09-lsp-and-dap
plan: 01
subsystem: tools
tags: [lsp, dap, jsonrpc, diagnostics, breakpoints]
provides:
  - Framed stdio sessions for a language server and a debug adapter
affects: [10-modes-and-learning]
---

# Phase 9 summary

`RpcConnection` spawns an argv command and frames Content-Length JSON over its stdio with a daemon reader thread (`read1`, so a quiet child never deadlocks the reader) and a close that always reaps the child. `LspSession` runs initialize, opens one document, and returns its `publishDiagnostics`; `DapSession` runs initialize, launch, breakpoints, `configurationDone`, waits for the `stopped` event, and reads threads plus the stopped thread's frames. `lsp_diagnostics` and `dap_stop` expose both through the registry with the workspace root jail; a string command and a non-positive breakpoint line are errors that start nothing. The roster lists both IDE names after the platform names, and the family roster assertions now compose the full order.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `72 passed in 3.56s` (`test_ide.py`: 5 passed; no fixture server left running)

Unverified: real language servers and adapters, multiplexing, config discovery, deferred diagnostics, the diagnostics ledger, writethrough, and attach.
