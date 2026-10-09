---
milestone: v12
name: Programming Desk merge
audited: 2026-10-09
status: passed
scores:
  requirements: 13/13
  phases: 4/4
requirement_disposition: all-wired
active_phase: none
open: []
exceptions: []
---

# v12 milestone audit: passed

**Scope.** Behavior-port the programming-desk pattern (source pin `9de3aa3`) under one Omega Prime bot. Desk tools are configured, the agent can work on a separate repo, subbots go through `delegate_task`, receipts are checked against captured commands, gates can target the work repo, and Grok Bot serves the result.

**Result.** DESK-01..11 and DONE-01, DONE-02 satisfied. No exceptions. Live service APIs were not called: this environment has no Railway, Greptile, Vercel, Play, or App Store credentials. That absence is recorded, not treated as a pass of a live call.

## Requirement-by-requirement

| Requirement | Status | Evidence |
|---|---|---|
| DESK-01 configured desk contexts | WIRED | `64-VERIFICATION.md`. Doctor green on memory, tools, substrate with no credentials. Shared memory store. Stores under `OMEGA_PRIME_STATE_DIR`. |
| DESK-02 work root | WIRED | `64-VERIFICATION.md`. Foreign tree editable; escape refused; ownership stays on the install root. `oneclick --work-root` forwards to the host. |
| DESK-03 delegate_task served | WIRED | Served count 109 on `setup_check`, dry-run manifest, self-test `list_tools`, and a throwaway SSE session. No provider env returns `not_configured: provider`. A scripted child turn returns in `test_delegate_parent_shim_runs_a_scripted_child`. No live model call was made. |
| DESK-04 lead pass | WIRED | `64-VERIFICATION.md`. Scheduler end-to-end intake to ack. `DeskDriver` ticks due passes. Live server starts it (`main`, `serve_sse`); registry construction does not. |
| DESK-05 target gates | WIRED | `65-VERIFICATION.md`. `qua_gates_run` selects Omega suites, a desk gate file, or pytest for another repo, and returns the runner exit code. |
| DESK-06 receipts and approver | WIRED | `65-VERIFICATION.md`. Captured command verifies; forged exit code fails; operator `ove` stamps a bot-00 receipt; the bot cannot approve itself. |
| DESK-07 service clients | WIRED, live unavailable | `65-VERIFICATION.md`. urllib clients behind env tokens; fake transport tests; `env={}` is `not_configured`. No credentials in this environment, so no live API call. |
| DESK-08 desk env | WIRED | `64-VERIFICATION.md`. Bus, docs index, and notify URL attach only when set. |
| DESK-09 truthful host | WIRED | `66-VERIFICATION.md`. Docs no longer claim 108 tools or an unserved `delegate_task`. `lead_roster_status` reports the seven absorbed seats. Template names the remaining doctor checks. |
| DESK-10 clone and desk call | WIRED | `66-VERIFICATION.md`. `oneclick --dry-run` exit 0. `oneclick --self-test` 22 pass / 0 fail, 109 tools. Separate SSE session called `lead_roster_status` (seven seats) and `delegate_task` (`not_configured: provider`). |
| DESK-11 three-source port | WIRED | `66-PORT-EVIDENCE.md` cites `omega_prime/agent/`, the roster/policy/registry, and the Prime trees plus `prime-agent.pin.json`. `setup_check` on this tree reports 109 served tools with Prime families off. |
| DONE-01 audit | WIRED | This file. |
| DONE-02 archive and gates | WIRED | Phase dirs moved to `milestones/v12-phases/`. Roadmap collapsed. Final tree: pytest 1942 passed, mypy 312 files, ruff clean, evals 26, assemble/catalog/setup_check exit 0 (109 tools). |

## Known limits

- Service clients are not proven against live Railway, Greptile, Vercel, Play, or App Store endpoints.
- `delegate_task` was not run against a live model. The served tool and the scripted child are what this environment can prove.
- `oneclick --self-test` calls `todo_read`. The desk call was a separate loopback SSE session, same host code.
