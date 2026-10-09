---
phase: 61-prime-loop-gap-closure
status: gaps_found
requirements_accounted_for: 32
wired: 27
broken: 3
human_needed: 2
auditor: FinalV10Integration (gsd integration-checker profile, read-only, unsigned)
supersedes: 61-INTEGRATION-pre-repair.md
full_report: 61-INTEGRATION-FULL32.json
---

## Integration Check Complete - FinalV10Integration (2026-10-09)

**Verdict: BLOCKED, on user decisions only.** All 32 IDs accounted for: **27 WIRED, 3 BROKEN (LOOP-07, REPO-04, DONE-01), 2 HUMAN_NEEDED (REPO-05, DONE-02)**. Baseline was 26/4/2. CONN-01 moved BROKEN -> WIRED. I found no code blocker. I wrote no files; repo status md5 is identical before and after.

### CONN-01 mechanical proof
All **37** registered Prime tools (RLM 7, Harness 6, Goals 5, Heartbeat 3, Autonomous 3, Messaging 2, Kernel 11) were driven through a granted `ToolRegistry`. Each returns `unknown_field` for an undeclared key and `unsupported_schema_version` for `schema_version: 999`, plus `bad_value` for 0. Every row is audited as `error` with `<code>: <reason>` and the file tree is unchanged: 37/37, 0 failures. The same holds over a real stdio MCP server for the 28 config-registrable tools. Every handler follows the declared-only convention (`**extra`, all params default `None`, `reject_extra` then typed `from_dict`). Rejected kernel requests import no `rlm`, build no kernel, create no files. Policy and approval run before decode. BUG-1 (heartbeat/kernel bypass) is repaired.

Residual literal-reading gaps (WARNING, not blockers under the documented tool-boundary scope): the loop calls `PrimeGoalStore.accrue_turn` / `driver.after_turn` directly, so `GoalsConnector.accrue` and `AccrueRequest` are dead in production (BUG-2). The kernel wire drops undeclared kwargs instead of rejecting them (BUG-3). Capability/domain failures keep an unprefixed `{'error': 'Type: msg'}` envelope.

### Open gates (honest)
| ID | Status | Why |
|---|---|---|
| LOOP-07 | BROKEN | Fixture half is satisfied and re-proved (6/6 on a pristine 79ff51af). The unmodified historical suite is **376 pass / 2 fail** (reproduced, exit 1). Needs a user-approved exception. |
| REPO-04 | BROKEN | `cargo metadata --locked --offline` on a source-only copy: **exit 101**. Dependabot has no cargo entry. Needs a packaging decision or an exception. |
| DONE-01 | BROKEN | No passing command can be cited for LOOP-07 or REPO-04. |
| REPO-05 | HUMAN_NEEDED | pytest 962 passed, setup_check 0, MCP serves. Native/upstream cargo builds were not run, and there is no published revision to clone. |
| DONE-02 | HUMAN_NEEDED | Nothing is committed/archived/published; needs DONE-01 and user authorization. |

### Cross-phase flows traced and run
Real `OmegaPrimeAgent` parent with `session_dir`: spawn -> collect -> list -> fresh-host recovery without replay (no answer text in list). Heartbeat: `heartbeat_set` -> real APScheduler fire -> same live session transcript, last_result persisted. Unknown session is an explicit error. Messaging: forged sender rejected. Autonomous: stops at `autonomous_max_turns`. Goal continuation: bounded to `goal_stale`. Kernel rlm bridge: spawn/collect/list/delete, bound progress accepted then throttled, no model -> explicit error. Truncated-JSON args become error rows and the tool is not run.

### Warnings re-graded
Resolved: W-1 (no CWD default), W-8 (atomic admission), W-9, W-10 (28 tools executed over stdio), W-11. Still open: W-2 (pin-drift test deleted), W-3, W-4 (heartbeat over MCP fires nowhere), W-5, W-6, W-7. New: N-1..N-8, including stale docs (agent-loop 'superset', migration omits kernel, CHANGELOG '109-tool roster'), a README config example that enables families with no production consumer, stale planning counters, default `max_children=1`, and publication hazards (`.phase61-review-smoke.py`, a 1.4 GB `openhands` binary, `openhands-stable.tgz`).

### Not run by me
Upstream Rust tests, native bridge build, cargo-deny, cloud CI, a published-clone run.

## Requirement rows

| ID | Status | Evidence | Limits / open |
|---|---|---|---|
| DISC-01 | WIRED | Archived documentation criterion; capabilities it maps (RLM, harness, goals, heartbeat, autonomous, messaging) now all execute: see RLM/HARN/LOOP rows. | Documentation criterion; inherited archival evidence. |
| DISC-02 | WIRED | Named integration points resolve in current code: registry.py:89 dispatch, assemble.py render, config.py, agent/rlm.py durability, agent/runtime.py. | Documentation criterion. |
| DISC-03 | WIRED | Pin 967eb13f... equals `git -C prime-agent rev-parse HEAD`; toolchain 1.98.1 present in VENDOR.md; retained baseline stated honestly as exit 101, 5089/2/19/3; 3 ACP skips in pin file. | Not a green workspace; the two ext4 failures are unwaived diagnostics. The pin-drift test file was deleted (W-2). |
| BUILD-01 | WIRED | CI reads the pin file, builds --locked, runs workspace tests with the skip set, and a separate job builds the bridge. | No cloud CI run claimed; native/ and deny.toml are untracked. |
| BUILD-02 | WIRED | cargo-deny licenses against upstream and against the native graph. | deny.toml untracked; no cloud run. |
| BUILD-03 | WIRED | Single toolchain source read by CI from the pin file; 1.98.1 toolchain present locally. | No test guards VENDOR.md vs pin.json since test_prime_pin.py was deleted (W-2); they agree today. |
| RLM-01 | WIRED | Real OmegaPrimeAgent parent with session_dir: rlm_spawn returned {rlm_child_id,name,session_dir,model}; rlm_collect returned status done/settled true/answer_preview 'child saw: child-only-task'. Child runner ran a real child OmegaPrimeAgent; crash -> status error covered by test_prime_failure_injection.py (passing). | Needs an explicit run_child; the default host has no runner. No production compose site calls register_rlm_tools (tests/catalog only). Default OmegaPrimeAgent.max_children is 1 and settled children count until deleted (observed 'RLM child limit reached (1)'). |
| RLM-02 | WIRED | list returns Prime status vocabulary (completed/running/error); kernel delete returned a metadata snapshot; fresh host after delete did not resurrect the deleted child. | Deleting a running child cannot kill its worker thread; late settle only writes the tombstone (documented). |
| RLM-03 | WIRED | Durable atomic JSON per child; a fresh RlmHost on the same real parent listed the settled child ('completed') without replaying (runner raised if called). Kernel bound progress: child flags [True,False] (accepted then throttled); root note -> accepted false. rlm_create_session has no cwd; supplied cwd -> unknown_field. | Durable root is parent.session_dir; require_parent now refuses a parent without it (W-1 resolved). One live host per (session_dir, owner name) is a documented assumption. Kernel model selector is explicit/caller chosen; no model inventory. Not a native daemon. |
| RLM-04 | WIRED | Child received only its own prompt (child transcript user rows == [prompt]); list rows and kernel list/delete contain no answer text ('child saw' absent); collect is the answer channel. | Answer is stored in the child's durable JSON under session_dir and spawn returns session_dir, so a parent with file tools could read it without collect (W-6, unchanged). |
| HARN-01 | WIRED | Six harness tools decode through typed requests; global_ is the only scope input; non-bool global_ -> bad_type. | Persisted entries only; entries are not auto-injected into the prompt. |
| HARN-02 | WIRED | refine returns the evidence-filtered diff and applies only evidence-backed proposals. | None new. |
| HARN-03 | WIRED | Rollback restores the prior memory entry exactly and removes the newly learned skill (assertions restored == before). | Audit trail is retained by design; history file does not rewind byte for byte. |
| HARN-04 | WIRED | System message bytes identical across turns before/after refine+rollback (model.seen[1][0] == base). | None. |
| LOOP-01 | WIRED | goal_set via the registered tool then goal continuation in the real loop: continuation prompt 'Continue working toward the goal: ship it. Next step: a.' repeated until goal_stale stop (turn_exit_reason goal_stale, 12 api calls, bounded). Pause/clear/complete/budget stops covered by test_prime_loop.py. | Observation: after goal_stale the public final_response was '' because the exhausted ScriptedModel returned empty continuations (test-double artifact, not a real-model claim). The MCP default registry publishes the goals binding but has no consuming loop in that process (W-4). |
| LOOP-02 | WIRED | heartbeat_set through the registered tool persisted a session_heartbeat row in cron JobStore; the real APScheduler fired it and re-entered the live bound session 'alpha': last_result 'beat reply', same transcript user rows ['go','beat prompt']. Unknown session -> explicit error {'error': "unknown heartbeat session: 'ghost'"}, no fresh conversation. | Needs a started runtime and a bound OmegaPrimeAgent in the same process. A heartbeat_set made over MCP persists but nothing starts the runtime there, and the result does not say so (W-4). |
| LOOP-03 | WIRED | autonomous_start max_turns=2 in the real loop stopped with autonomous_stop(autonomous_max_turns), turns 2; gate/budget/minute/token stops in test_prime_loop.py; argv gates only. | autonomous_completed on an incomplete boundary is the library stop code, not proof of work. |
| LOOP-04 | WIRED | alpha sent to bob through agent_message_send (delivered sender 'alpha'); sender override -> unknown_field; unknown recipient -> typed unknown_recipient; observe takes no session (cross-session read impossible). | In-process explicit composition. No production compose site registers messaging; MCP default registry skips it; no automatic inbox injection. |
| LOOP-05 | WIRED | All 7 family flags default False. Shipped assembled prompt names none of the Prime tools; --enable-family rlm,heartbeat to a tmp output names exactly those tools. Real stdio MCP: default 108 tools, 0 Prime; enabling 5 families gives exactly 28 more (136). catalog --check and assemble --check exit 0. | 1) Config reaches the shipped prompt only through render(config=...)/--enable-family; production never feeds load_config() into the prompt (W-3). 2) The static roster YAML lists all 37 names (roster is 146 names); the effective offered roster is roster intersect registered (W-5). 3) rlm and messagi… |
| LOOP-06 | WIRED | Hook failures emit redacted prime_degraded and veto implicit continuation; provider errors/interrupts bypass the wrapper; heartbeat sink isolation; malformed stored goal status surfaces as a registered-tool typed error. | None new. |
| LOOP-07 | BROKEN | Part A (loop transcript fixture) satisfied and independently re-proved: the six fixture cases replayed against a pristine 79ff51af checkout match 6/6, and the current default-off Agent matches the fixture (test passes). Part B ('pre-v10 suite passes unmodified') is NOT met: historical tests + current source = 376 passed / 2 failed (exit 1), both in test_too… | The two failures look like incidental pins to the historical catalog/roster fixture, not a behavior regression with flags off; the second failing test in my replay is partly a replay-construction artifact (historical committed catalog vs current render). Receipts name different second tests across… |
| CONN-01 | WIRED | Mechanical proof over all 37 registered Prime tools in 7 families (RLM 7, Harness 6, Goals 5, Heartbeat 3, Autonomous 3, Messaging 2, Kernel 11): through a granted registry each tool returns code=unknown_field for an undeclared key, unsupported_schema_version for schema_version 999 and bad_value for 0, all audited verdict=error '<code>: <reason>', with the… | Scope reading, stated plainly: WIRED for the registered-tool boundary (the contract docs/connectors.md and ADR define) and the kernel bridge (host.py builds typed requests from declared keys). Literal 'every capability call' still has loop-internal gaps (N-1, N-2 in findings): the loop's goal accru… |
| CONN-02 | WIRED | Request/response round-trip and strict-decoder tests for the five original adapters; the two new adapters are covered by boundary tests (33 and 61 cases) and I verified 12/12 new request types round-trip from_dict(to_dict())==x. | docs/connectors.md rule 4 says round-trip is pinned by test_prime_contracts.py for every request type; heartbeat and kernel requests are not in that file (grep: no hits). Those two adapters have no typed response views, so 'both sides' is request-side typed, response-side the runtime's own envelope. |
| CONN-03 | WIRED | Raise/timeout/bad-payload each reach the model as a structured error row, then the loop recovers; truncated-JSON arguments are an error row and the tool is not executed. My flows reproduced truncated JSON (c4), unknown_field (c5), future version (c6), bad heartbeat type (c8), refusal-then-recovery. | RLM failure-injection tests use a stub parent for most cases; I additionally ran a real OmegaPrimeAgent parent. |
| CONN-04 | WIRED | Six source-derived fixtures at pin 967eb13f pass against the ported implementation. | Fixtures are derived by reading the pinned sources; there is no executed Rust-vs-Python differential. Upstream Rust diagnostics (exit 101) are retained, not rerun. |
| REPO-01 | WIRED | Header/source-policy tests pass in the 962 run. | native/ and deny.toml are untracked in git. |
| REPO-02 | WIRED | Required root files present; clone URL in README is omes-bot.git. | Dependabot covers pip and github-actions only (REPO-04). |
| REPO-03 | WIRED | Docs exist, link/GitBook tests pass, and the central claims I spot-checked match code (rule 5, RLM section, parity paragraph, 376/2 stated as not green). Rule 5's former heartbeat/kernel overclaim is now true. | Minor stale/imprecise statements listed in N-4. |
| REPO-04 | BROKEN | Criterion needs 'dependabot for cargo/pip/github-actions'. Cargo is not configured, and cannot be: cargo +1.98.1 metadata --locked --offline on a source-only copy exits 101 (crossterm manifest missing under prime-agent/vendor). cargo-deny and pip-audit are present (rust-parity.yml:72,141; supply-chain.yml:13-22). | Unwaived. Needs the user's decision: make the pinned checkout repository-fetchable (read-only submodule/gitlink) or approve an explicit criterion exception. Neither has been approved or done. |
| REPO-05 | HUMAN_NEEDED | Executed by me from the repo: pytest omega_prime/tests -q (962 passed), setup_check --root <repo> (exit 0), stdio mcp_server --root (served 108/136 tools). Repair-wave evidence records a fresh Python 3.12 venv install + fresh pin checkout: 949 passed/13 skipped, setup ok. | Needs: (a) a published revision to clone (all work is uncommitted; the canonical clone cannot reproduce it), or the user's acceptance of the isolated current-source snapshot, and (b) a current receipt (or acceptance) for the optional upstream cargo build and the native bridge build; 13 tests skip o… |
| DONE-01 | BROKEN | 'A passing command + exit code for every v10 requirement' cannot be cited: LOOP-07 is exit 1 (376/2) and REPO-04 is exit 101; REPO-05 awaits publication. | Cannot pass until LOOP-07 and REPO-04 are resolved or explicitly excepted by the user; the parent then writes the audit. |
| DONE-02 | HUMAN_NEEDED | No completion, archive to milestones/v10-phases/, cleanup, commit, PR or push has happened. | Needs DONE-01 first, then the user's authorization for archive/cleanup and ownership-safe publication (stray files in findings N-7). |

## Flows

| Flow | Status | Limit |
|---|---|---|
| Model -> OmegaPrimeAgent loop -> registry (policy -> approval -> decode) -> connector -> capability | WIRED | Observed rows: truncated JSON error row; unknown_field; unsupported_schema_version; bad_type; refusal then recovery. Capability failures keep an unprefixed 'Type: message' envelope. |
| RLM spawn/collect/list/recover with a real OmegaPrimeAgent parent (session_dir) | WIRED | Needs explicit runner; no production compose site; default max_children=1 (settled children count until deleted). |
| Kernel rlm bridge | WIRED | Model selector explicit; no inventory; wire silently drops undeclared kwargs (N-2); progress identity only from worker context. |
| Goal and autonomous continuation hooks | WIRED | Loop calls store.accrue_turn/driver.after_turn directly (typed response views only; GoalsConnector.accrue unused in production, N-1). Only in a process where an OmegaPrimeAgent shares the registry. |
| Heartbeat re-entry chain | WIRED | Orphan where no agent binds/starts the runtime (MCP default registry); tool result gives no warning (W-4). |
| Refusal scoping | WIRED | Exercised: unapproved goal_clear refused, goal_set approved, model recovered; turn ended text_response. |
| Effective prompt/roster/catalog default-off | WIRED | Config -> shipped prompt is manual (W-3); static roster YAML is a superset (W-5). |
| Installed stdio MCP serving Prime tools | WIRED | I executed 56 Prime tool calls over real stdio (28 tools x 2 rejection probes), plus the recorded evidence smoke. RLM and messaging are never served over MCP. |
| Pinned parity fixtures and pre-v10 transcript comparator | WIRED for the 6 goldens and 6 parity fixtures | Full unmodified historical suite is 376/2 (LOOP-07 BROKEN); parity fixtures are source-derived. |

## Findings

### Blockers (user decisions only; no code blocker)

- F-1 LOOP-07: the literal unmodified historical suite is 376 passed / 2 failed (reproduced independently, exit 1); unwaived. Needs a user-approved exception or documented updated pins.
- F-2 REPO-04: Cargo source-only resolution exits 101 (reproduced); Dependabot has no cargo entry; no approved packaging choice. Needs the user's decision.
- F-3 DONE-01/DONE-02/REPO-05: audit cannot cite passing commands for LOOP-07/REPO-04; nothing is committed or published; lifecycle needs the user. No code blocker found: CONN-01's former heartbeat/kernel blocker (BUG-1) is repaired.

### Actionable items and warnings

- **BUG-2** (WARNING (literal CONN-01 reading); not a blocker under the documented tool-boundary scope): The loop's per-turn goal accrual and driver consult bypass the typed AccrueRequest/Connector request path; the connector's accrue is dead in production. Repair: Route evaluate_goal through GoalsConnector.accrue(AccrueRequest(usage=...)) (and an autonomous consult request) or amend CONN-01/docs/connectors.md to scope the typed boundary to the tool and kernel surface, with the user's approval.
- **BUG-3** (INFO/WARNING): rlm.run/rlm.create_session read only name/model/thinking(/cwd) from kwargs and silently ignore other kwargs and top-level keys; rlm.host_request is reachable from kernel cells. Nothing undeclared is honoured, but it is not rejected, and the wire carries no schema_version. Repair: Reject unknown kwargs/top-level keys with PrimeError('unknown_field'), if the pinned SDK is confirmed to send only the declared set.

- W-1 RESOLVED: durable RLM root no longer defaults to CWD (require_parent, agent/rlm.py:250-280; OmegaPrimeAgent(session_dir=...)).
- W-2 OPEN: test_prime_pin.py is deleted and nothing replaces it. Pin and VENDOR.md agree today (checked by hand); drift is unguarded.
- W-3 OPEN (accepted): no production path feeds load_config() into the shipped prompt; render(config)/--enable-family are manual.
- W-4 OPEN: MCP default registry publishes goals/autonomous/heartbeat tools/bindings without a consuming loop or started heartbeat runtime; heartbeat_set returns {'scheduled','session'} with no delivery caveat.
- W-5 OPEN (accepted): static roster YAML lists all 37 Prime names (146-name roster); effective offered roster is filtered at serve time (mcp_own.py: 108 default).
- W-6 OPEN: child answer is stored in durable JSON under session_dir and spawn returns session_dir; a parent with file tools could read it without collect.
- W-7 OPEN: 118 dirty paths, uncommitted; native/, deny.toml, .planning/phases etc. untracked. See N-7.
- W-8 RESOLVED: admission (name, max_children, depth, registration) is one registry-lock section (agent/rlm.py:624-636).
- W-9 RESOLVED: schema_version < 1 -> bad_value (prime/types.py:27-28).
- W-10 RESOLVED by my run: 28 Prime tools executed over a real stdio MCP server, each rejecting undeclared key and future version with isError and typed codes.
- W-11 RESOLVED: connectors.md rule 5 heartbeat/kernel statement is now true (verified: rejected kernel requests import no rlm, build nothing, write nothing).
- N-1 Loop-internal capability calls (goal accrual, continuation prompt, driver.after_turn) bypass the typed request adapter; GoalsConnector.accrue/AccrueRequest dead in production (BUG-2). Literal-reading CONN-01 gap.
- N-2 Kernel host wire silently drops undeclared rlm.run/create_session kwargs (BUG-3).
- N-3 Post-decode capability/domain failures use the unprefixed {'error':'ValueError: ...'} envelope with no code (43/767 fuzz cases: duplicate name, unknown id/spec, 4000-char goal, NameError, harness_get miss, heartbeat_clear whitespace id). Intentional for pinned Prime error text but inconsistent with the typed envelope.
- N-4 Doc imprecision: docs/agent-loop.md:194-195 says 'the assembled prompt lists an allowed superset' (the default assembled artifact names no Prime tools; the template/roster/policy are the superset); docs/migration.md:36-39 omits the 11 kernel tools from 'New rostered tool families'; CHANGELOG.md:231 '109-tool roster' is stale (roster is 146 names; 108 MCP default is correct); README config example enables rlm and messaging, which no production site consumes; connectors.md rule 4 claims round-trip is pinned by test_prime_contracts.py for every request type (heartbeat/kernel absent there; I verified they round-trip).
- N-5 Planning bookkeeping stale: REQUIREMENTS.md leaves RLM-03/04, LOOP-05, CONN-01/03 unchecked and cites the older '22 wired / 10 broken'; ROADMAP 61-03..06 unchecked; STATE.md cites 739/726 counts and 'Finishing 61-06' (current full run: 962 passed, 0 skipped here; evidence fresh install 949 passed / 13 skipped).
- N-6 Default Agent.max_children is 1 and settled children count until rlm_delete_subagent; a default OmegaPrimeAgent parent can hold one child (observed 'RLM child limit reached (1)').
- N-7 Publication hazards at the repo root, untracked: .phase61-review-smoke.py (stray review script that mkdtemps into cwd), openhands (1.4 GB executable) and openhands-stable.tgz (707 MB). A blanket git add would pull them in.
- N-8 Historical replay receipts name different second failing tests (earlier: test_template_names_nothing_that_is_not_on_disk; repair-wave and mine: test_check_passes_on_committed_file_and_fails_on_drift). Count and character agree (376/2, catalog/roster pins); docs say 'two obsolete incidental-pin failures', which I did not find disproved.

## Commands the checker ran

- [exit 0] cwd=scratch, PYTHONPATH=repo, venv python: conn01.py (my script) - 37 Prime tools across 7 families via granted ToolRegistry, 4 probes each (undeclared key, schema_version 999, future version + undeclared key, schema_version 0) plus before/after file-tree sha256 snapshot: 37/37 pass, 0 failures, 148/148 audit rows verdict=error with typed code
- [exit 0] conn01b.py (my script): catalog full_inventory_registry contains all 37 names; ungranted write tool -> 'approval required' before decode; policy-forbidden read tool -> 'policy forbids' before decode; non-object/truncated args handled by registry; handler convention check (has **extra, no required positionals, declares schema_version) on 37/37 handlers: no CONVENTION-BREAK
- [exit 0] pytest 11 files (test_prime_tool_authorization, _heartbeat_boundary, _kernel_boundary, _tool_surface, _goal_surface, _rlm_surface, _loop_boundaries, _failure_injection, _contracts, _parity, _regression) -p no:cacheprovider: 267 passed
- [exit 0] pytest omega_prime/tests (full, from scratch cwd, PYTHONDONTWRITEBYTECODE=1): 962 passed, 12 warnings, 0 skipped, 0 failed (31.98s)
- [exit 0] python -m omega_prime.tooling.catalog --check: docs/tool-catalog.md up to date
- [exit 0] /root/.hermes/cache/scratch/phase61-probe/probe.py from scratch cwd: defects_present [] (tree = repo omega_prime)
- [exit 1] python -m omega_prime.assemble --root <repo root> --check: missing roster (wrong --root, my invocation error; root is the package dir)
- [exit 0] python -m omega_prime.assemble --root <repo>/omega_prime --check: OMEGA_PRIME up to date
- [exit 0] python -m omega_prime.assemble --root <repo>/omega_prime --enable-family rlm --enable-family heartbeat --output /tmp/final_enabled.xml: enabled prompt names exactly the 7 rlm_* and 3 heartbeat_* tools; shipped OMEGA_PRIME.xml and template contain 0 of the probed Prime names; roster YAML contains them (static superset)
- [exit 0] config probe: PRIME_FAMILIES=7, all default False; env OMEGA_PRIME_PRIME_RLM_ENABLED=1 flips rlm; disabled_family_tools(None)=37, with rlm enabled=30
- [exit 1, expected] historical suite replay #1 (git archive 79ff51af + current non-test .py overlaid, system python on PATH): 375 passed / 3 failed - environment artifact (apscheduler absent from system python in assemble subprocess)
- [exit 1, expected] historical suite replay #2 (same tree, venv first on PATH, PYTHONPATH=/tmp/final_hist): 376 passed / 2 failed; failures test_tool_catalog.py::test_render_covers_roster_once_with_families and ::test_check_passes_on_committed_file_and_fails_on_drift. LOOP-07 literal criterion reproduced unmet
- [exit 0] /tmp/final_oracle.py against a PRISTINE git-archive of 79ff51af (PYTHONPATH=/tmp/final_hist_pure, omega_prime resolved from there): replayed the six fixture cases, 6 of 6 match fixture expected (pre_v10_loop_transcript.json); current comparator test also passes
- [exit 0] flows.py (my script): real OmegaPrimeAgent parent (session_dir) + child OmegaPrimeAgent runner through registry: spawn/collect/list, truncated-JSON row, unknown_field row, future-version row, heartbeat_set, bad-type heartbeat, goal_set; fresh RlmHost recovery without replay; list has no answer text
- [exit 0] flows2.py (my script, run twice; first run's manual _fire_job was a no-op because due_at was in the future): real APScheduler fire re-enters the live session 'alpha' (same transcript grew, last_result 'beat reply'); ghost session -> explicit error; forged sender -> unknown_field; unknown recipient -> typed unknown_recipient; autonomous_start max_turns=2 -> autonomous_stop(autonomous_max_turns); refusal then recovery
- [exit 0] kernel_flow.py (my script, run twice; first run used wrong request type names and default max_children=1): pinned rlm InProcessHost with a real OmegaPrimeAgent parent/child: rlm.run/collect/list_subagents/delete_subagent, bound progress accepted then throttled, no model -> explicit error, no answer in list/delete, delete not resurrected
- [exit 0] noimport.py (my script): all 11 kernel tools rejected with bogus key / schema_version 5 / schema_version 0 -> 'rlm' not in sys.modules, host not imported, no files created
- [exit 1 x2, then 0] mcp_own.py (my script; two script attribute-name errors server_info/is_error then pass): real stdio `python -m omega_prime.mcp_server`: default-off serves 108 tools, 0 Prime; 5 config-registrable families enabled serves 136 (28 Prime); all 28 reject undeclared key (unknown_field) and schema_version 999 (unsupported_schema_version) with isError true; rejected calls create no files
- [exit 0] fuzz.py (my script, one script bug fixed): 767 wrong-type/whitespace/oversize cases over every declared param of 37 tools: 43 untyped-envelope cases, all post-decode domain/capability failures (unknown id, duplicate name, unknown factory spec, 4000-char goal, NameError in a cell); zero decode-boundary failures
- [exit 101, expected] cargo +1.98.1 metadata --locked --offline on a copy of native/omega-prime-prime without prime-agent/ in /tmp/final_src_only: failed to read prime-agent/vendor/crossterm/Cargo.toml. REPO-04 reproduced
- [exit 0] python -m omega_prime.setup_check --root <repo>: roster/template/assembly ok, registry serves 108 roster tools
- [exit 0] ruff check --no-cache omega_prime/ ; ruff format --check --no-cache (280 files formatted); mypy --cache-dir=/dev/null omega_prime/ (245 files, no issues; exit was of the piped tail); evals runner: 26 PASS; actionlint .github/workflows/*.yml
- [reads only] git status, git cat-file/rev-parse, grep, file reads, sqlite/json reads; python round-trip of the 12 heartbeat/kernel request types (12/12 from_dict(to_dict())==x)

## Separation of evidence

- **Observed:** Everything in checks_run: the 37-tool CONN-01 proof, stdio MCP runs, full test run 962 passed, historical replay 376/2, pristine-oracle 6/6, real-agent RLM/heartbeat/messaging/autonomous/kernel flows, cargo metadata exit 101, lint/type/evals/actionlint/catalog/assemble/setup_check, repo status md5 unchanged.
- **Source:** File:line citations from direct reads of tools/*.py, prime/*.py, agent/{runtime,rlm,prime_hooks}.py, prime_kernel/host.py, registry.py, assemble.py, config.py, mcp_server.py, workflows, dependabot.yml, docs, planning files.
- **Inference:** That the two LOOP-07 failures are incidental pins (consistent with test text and the earlier receipts, not shown to be behavior-neutral beyond the fixture); that 13 fresh-install skips are the native-bridge-dependent tests (recorded evidence, not re-run); that BUG-3's silent drop is unreachable by anything harmful (nothing undeclared is read, not proven for all SDK versions). Not run by me: Rust upstream tests, native build, cargo-deny, cloud CI, a clone of a published revision.

The previous pre-repair report is preserved as `61-INTEGRATION-pre-repair.md`; the complete
machine-readable report is `61-INTEGRATION-FULL32.json`.
