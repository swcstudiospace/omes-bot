---
phase: 61-prime-loop-gap-closure
status: gaps_found
requirements_accounted_for: 32
wired: 22
broken: 10
auditor: gsd-integration-checker
---

## Integration Check Complete

**Verdict: BLOCKED. All 32 IDs are accounted for: 22 WIRED within the explicit evidence scopes below; 10 BROKEN against at least one named criterion.** WIRED is an integration disposition, not an assertion that a fresh cloud job or every external service was executed. The repaired existing-loop paths are real, but neither old archive status nor 686 passing tests establishes blanket 32/32 satisfaction.

This audit used the exact installed GSD integration-checker profile, current REQUIREMENTS, all archived 53–60 SUMMARY/VERIFICATION reports, both discovery maps, Phase 61 summaries/review/security/validation/evidence, and the relevant runtime, registry, tools, connectors, native bridge, workflows, and public documentation. Legacy SUMMARY prose supplied requirement attribution where frontmatter IDs were absent. No files were changed. No builds, tests, linters, formatters, smoke commands, or upstream Rust tests were run by this auditor.

### Wiring Summary

**Connected:** 16 explicitly examined key exports/contracts have callers: `load_config`, `prime_enabled`, `family_config`, `RlmHost`, `HarnessState`, `refine`, `PrimeGoalStore`, `AutonomousDriver`, `SessionRegistry`, `guarded_hook`, `prime_hooks_from_bindings`, `HeartbeatRuntime`, `GoalStatusView`, `VerdictView`, `PrimeProviderModel`, and `OmegaPrimeAgent`. RLM and messaging connections include explicitly composed/manual consumers, not automatic default delivery.

**Orphaned from production consumers:** 5 connector classes and 8 typed request classes. They are exercised in tests, so they are not wholly unused code; their missing connection is the product boundary promised by CONN-01.

**Missing/broken:** 8 mandatory integration/acceptance paths, detailed as INT-01–08. The additional default-native child-delivery path is explicitly unconfigured, not proved by the scripted isolation receipt.

| Provider phase | Provides | Consumer and observed connection | Disposition |
|---|---|---|---|
| 53 | Capability/overlap maps; upstream pin and recorded baseline | Later ports, adapter fixtures, VENDOR and CI reference pinned contracts | WIRED as discovery/provenance, not execution of all mapped capabilities |
| 54 | Pinned Rust workflow and license policy | `rust-parity.yml` checks out the pin and configures locked build/test and licenses; independent native job has its own checkout/build/license steps | WIRED configuration; no current cloud pass claimed |
| 55 | Family config, RLM host/handles/statuses, RLM tool registration | Host is called by explicit registered tools and kernel host; scripted spawn/collect/list/delete consumers exist | WIRED scripted contracts; durable/progress/result-channel gaps remain |
| 56 | Harness CRUD/refine/snapshots/rollback | Registered `harness_*` handlers load/save state and call real refinement; current repair restores prior entries | WIRED |
| 57 → 61 | Goal store, autonomous driver, degradation, heartbeat jobs, messaging | Registry runtime bindings → `OmegaPrimeAgent` → existing conversation-loop boundaries; heartbeat runtime binds named live sessions and persists outcomes | WIRED repaired loop paths; static prompt filtering and historical fixture comparison are BROKEN |
| 58 | Five typed/versioned connectors and request decoders | Standalone adapter tests call capability implementations; real tools bypass connector classes | BROKEN at production consumer boundary |
| 59 → 61 | Public docs, licensing, supply-chain and quickstart | Native headers/license/build and corrected clone/MCP paths are evidenced; Cargo updater and clean-clone suite prerequisites are missing | Mixed; REPO-04 and full REPO-05 BROKEN |
| 60 → 61 | Audit and milestone lifecycle | Old archive is historical; reopened Phase 61 remains active and evidence explicitly says milestone incomplete | BROKEN current closeout |

### API Coverage

**Consumed:** 2 product-owned MCP operations, `tools/list` and `tools/call`, have an actual stdio client consumer. The final receipt initialized MCP, listed 108 tools, read 1160 bytes from the actual documented coding root, and matched the response to disk.

**Orphaned:** 0 of those two owned MCP operations. Separately, all five connector-class APIs lack production callers. Listing 108 tools does not prove execution of 108 handlers. This is a Python/MCP product audit, not a Next.js/HTTP-route audit.

### Auth Protection

Web login/private-page auth is **not applicable** to this milestone surface. The applicable boundary is registry roster/policy/approval enforcement. Both MCP and registered-agent dispatch reach `ToolRegistry.dispatch`; policy and required approvals precede handler invocation. Current real-native evidence proves refusal does not invoke the denied handler or produce its side effect. Provider credentials are explicitly supplied or broker-resolved; a localhost SSE peer is not a production authentication test. No new unprotected HTTP application route is identified in these integration paths.

### E2E Flows

**Complete scoped flows: 9.** These are specific traced paths, not blanket capability acceptance:

1. **Persistent goal control:** registered goal tools → fresh `PrimeGoalStore`/sidecar → actual model-call usage → `evaluate_goal` at the existing text boundary → continuation or authoritative pause/clear/completion/budget stop → persisted counters and honest result metadata.
2. **Autonomous control:** registered start/stop → live holder/driver → once-only accounting → turn/token/time bounds → actual argv quality-gate execution → gate/limit/refusal/incomplete stop. Stopped outcomes remain authoritative until explicit restart; a gate pass is not goal completion.
3. **Named scheduled heartbeat:** registered schedule → existing JobStore/APScheduler → captured named runner → foreground lease wait without holding bookkeeping locks → the owning agent's real loop → persisted result/history → list/clear/close. Current receipts include independent alpha/beta sessions, clear during a beat, no resurrection, overdue catch-up, redacted owning-session failure, and settled shutdown.
4. **Registered harness refine/rollback:** disk-backed CRUD → pre-refinement snapshot → evidence-backed changes and reviewable diff → reload/read → registered rollback restoring prior entries. Current registered proof also keeps base system-prompt bytes unchanged over two actual turns. Audit history is retained; this is not a claim that the entire serialized history file rewinds byte-for-byte.
5. **Explicitly registered messaging:** two named registries → approval-marked send → shared session inbox → recipient's rostered observe → body/read state returned. This is the manual in-process contract, not automatic inbox injection into native conversations.
6. **Real native provider tool round:** `from_prime` → `PrimeProviderModel` → actual Rust `pa_ai` completion against local SSE → registered actual-disk read → tool-result row → next completion → final response, preserving native message metadata.
7. **Existing-loop error/refusal handling:** real hook exceptions → redacted structured degradation → valid normal response without extra continuation; registry denial remains refusal. Paid calls before provider failure are charged once and the original provider error remains an error, not a success or a completion-gate invocation.
8. **Explicit scripted child isolation:** actual parent agent → `RlmHost` with an explicit scripted child runner → separate child agent/registry/system prompt → collect. The receipt proves the parent-only marker is absent from child model input. It does not prove default native child delivery or the whole RLM-04 collect-only criterion.
9. **Repaired URL/install/setup/MCP boundary:** canonical repository clone succeeds; a new isolated venv installs the actual current source; setup and exact stdio MCP list/read complete. This receipt does not execute the full quickstart suite from the clean cloned source tree.

**Broken acceptance flows: 8**, corresponding to INT-01–08 below. An additional inherited **default native RLM spawn → delivered child** flow is unconfigured: `run_child=None` reaches the explicit no-runner error. It must not be reported as an exercised native child flow.

### Detailed Findings

#### INT-01 — BLOCKER: Typed connector boundary is absent

**Requirements:** CONN-01, CONN-03.

`RlmConnector`, `HarnessConnector`, `GoalsConnector`, `AutonomousConnector`, and `MessagingConnector` are instantiated by tests, not production tools/runtime. The associated `SpawnRequest`, `CollectRequest`, `ProgressNoteRequest`, `UpsertRequest`, `SetGoalRequest`, `AccrueRequest`, `StartRequest`, and `SendRequest` decoders likewise have no production consumer.

Actual handlers in `omega_prime/tools/{rlm,harness,goals,autonomous,agent_message}.py` call hosts/stores/drivers directly and serialize ad-hoc dictionaries/dataclasses. `prime_hooks.py` uses `GoalStatusView` and `VerdictView` for two loop outputs; that does not connect the five adapter classes or validate incoming tool payloads. `ToolRegistry.dispatch` checks policy/approval but does not perform the versioned decoder validation.

The archived Phase 58 declaration that every Prime call crosses an adapter is therefore false. CONN-02's standalone request/response tests remain legitimate adapter tests, but do not validate the actual consumer boundary. CONN-03's seven historical tests also do not demonstrate the promised complete loop path: `test_prime_failure_injection.py` uses `SimpleNamespace` plus direct `guarded_hook` calls, calls the next wrapper invocation 'the loop continues', and tests timeout/malformed input directly against orphaned adapters. Current real goal/driver and heartbeat degradation evidence supports LOOP-06; it does not retrofit every adapter raise/timeout/bad-payload case into a registered consumer E2E proof.

**Missing steps:** tool dispatch → typed/versioned request adapter → capability → typed response → consuming loop; actual full failure-kind tests through that path.

#### INT-02 — BLOCKER: Durable child sessions and progress delivery are not implemented end-to-end

**Requirement:** RLM-03.

`omega_prime/agent/rlm.py:419–445` creates a `.jsonl` path with `touch()`, optionally calls `session_store.create`, then launches the same ephemeral executor child used by spawn. No production caller supplies that session store. The JSONL file is not populated with the child prompt, transcript, result, or recoverable child identity; no reload/reattach consumer is connected. `test_rlm.py:236–241` checks that the file exists and the child is listed, not durability. Child roster records still have `active_session_id=None` and `session_id=None`.

The kernel host's `rlm.progress.note` branch in `omega_prime/prime_kernel/host.py:152–155` only appends to `self.notes` and always returns `accepted=True`. It does not update the owning child's parent-side snapshot or enforce its 10-second acceptance throttle. The pinned Prime client enforces note length but delegates acceptance/throttling to the host. The direct Python host progress tests exercise a manually supplied child ID, not a child-bound progress bridge.

**Missing steps:** child execution → persisted session records → recovery/inspection; child-bound progress → owning parent child registry → acceptance/throttle result. The new scripted isolation receipt repairs neither connection.

#### INT-03 — BLOCKER: Literal collect-only result visibility is not satisfied

**Requirements:** RLM-04; related CONN-01.

The current isolation proof establishes independent child context, but the other half of RLM-04 says parent results are visible only through collect. `_Child.to_subagent()` in `agent/rlm.py:178–190` puts `answer_preview` into `RLMSubagent`. The registered list/delete handlers serialize that dataclass directly, and the kernel `_subagent_payload` also emits `answer_preview`. A parent can therefore obtain child answer content through list/delete without collect.

The pinned upstream roster also supports `answer_preview`; that explains the inheritance but is not an approved exception to the current literal requirement. The orphaned `RlmConnector.list_subagents` view omits answer preview, which further demonstrates that bypassing the promised adapter matters. **Context isolation is proved for the explicit runner; full RLM-04 is not.**

#### INT-04 — BLOCKER: Disabled-family prompt/roster filtering is absent

**Requirement:** LOOP-05.

Default-off config and runtime registry filtering are real. However, `omega_prime/prompts/bot-00-omega-prime.xml:165–202` and the static roster contain the Prime family names unconditionally. `omega_prime/assemble.py::render` does not consume family config or filter the prompt roster. With flags off, the assembled prompt remains the allowed superset of all family names.

The shared directive to use only live offered tools reduces misuse, and current docs acknowledge this design, but neither makes a disabled family **absent from roster and prompt**, as the unchanged requirement demands. Documenting the weaker behavior is not acceptance or a user-approved scope change.

#### INT-05 — BLOCKER: Historical transcript fixture connection is missing

**Requirement:** LOOP-07.

`test_prime_loop.py:620+` compares two executions of current code with the same synthetic script and system prompt. `test_prime_regression.py` checks absence of Prime events and live default-registry tools. Neither reads a recorded pre-v10 transcript fixture. Archived `57-01-SUMMARY.md:74–78` explicitly says the recorded golden transcript was replaced by these assertions; Phase 57 CONTEXT and current REQUIREMENTS still demand the fixture comparison.

Current 686-pass regression is valid evidence of current tests passing, not a historical golden comparison or proof that static prompt assembly is bit-for-bit pre-v10. No recorded baseline → current-transcript comparator is connected.

#### INT-06 — BLOCKER: Cargo updater and fetchable source dependency chain are missing

**Requirement:** REPO-04.

`.github/dependabot.yml` configures pip and GitHub Actions only. `native/omega-prime-prime/Cargo.toml` requires path dependencies and the crossterm patch under the ignored `/prime-agent/` tree (`.gitignore`). The evidence's source-only fixture copies all native source files, manifest, and lockfile, then runs actual resolving `cargo metadata --locked`; it exits **101** on the missing required crossterm manifest. An earlier `--no-deps` result is not resolution proof.

The primary Dependabot Cargo FileFetcher uses `fetch_file_from_host(path, fetch_submodules: true)` and raises `PathDependenciesNotReachable` for required missing manifests. A pinned read-only gitlink is therefore an **unapproved candidate**, not a shipped or proved solution. No Cargo Dependabot success or scope exception exists. Passing license and pip-audit gates do not replace the missing ecosystem.

#### INT-07 — BLOCKER: Clean-clone quickstart/Python CI cannot reach the full suite prerequisite

**Requirement:** REPO-05; related REPO-02, LOOP-07, DONE-01.

The clone URL, isolated dependency installation, setup, and actual MCP CLI are genuinely repaired. A remaining cross-environment connection is missing:

- README quickstart clones this repository, installs it, then immediately runs the full suite. The upstream clone appears later in the separate dual-toolchain instructions.
- `.github/workflows/ci.yml`'s Python `verify` job performs product checkout/install and runs the full suite, with no pinned Prime checkout step.
- `test_prime_kernel_host.py:40–41` unconditionally reads `prime-agent/Cargo.toml` through `workspace_members()` and imports the pinned runtime. Cell/skill tests also unconditionally consume that ignored checkout.
- `omega_prime/tests/conftest.py` only isolates PyRIT data; it does not provision or skip the missing upstream checkout. `checkout.py::workspace_members` directly reads the absent path. Separate Rust/native CI jobs have their own filesystem and do not supply the Python job.

**[INFERENCE from the source trace, not a newly executed failure]:** a clean repository checkout running the documented quickstart or Python CI suite will hit the missing pinned checkout, including `FileNotFoundError` for `prime-agent/Cargo.toml`. The fresh-venv evidence installs the actual existing `/root/src/repos/omega-prime` source and its setup output names that tree; it is not a full-suite run from the clean cloned tree. The local 686-pass receipt must remain valid local evidence, not a fresh-clone/cloud pass claim.

**Missing step:** documented clean environment / Python CI checkout → pinned upstream runtime/skills prerequisite → full suite.

#### INT-08 — BLOCKER: Current factual closeout is not complete

**Requirements:** DONE-01, DONE-02.

REPO-04 is explicitly blocked, and the additional unsupported criteria above prevent a factual passing command for every requirement. Phase 61 evidence says `milestone_complete=false`, `all_product_gates_passed=false`, and canonical status `human_needed`. The old archived 32/32 audit accepts omitted Cargo automation as tech debt and treats standalone tests/file presence as integration; its status cannot close the reopened milestone. Phase 61 remains in the active phase directory. Do not archive, publish, or mark the reopened milestone complete.

### Evidence and Historical Limits

- **Current parent-executed gates:** final full suite **686 passed, 12 warnings, exit 0**; affected suite **234 passed, exit 0**; evals **26 passed, exit 0**; Ruff, mypy, format, prompt/catalog/setup/config checks exit 0. These were read from `61-EVIDENCE.json`, not rerun here. The earlier 689-pass result predates retirement of three incidental source/default tests.
- **HARN-03/HARN-04:** before/after receipts show the old rollback defect and its repair. Current registered refinement restores the prior learned entries, removes the introduced skill on rollback, and preserves fixed base-prompt bytes over two turns. These repairs are accepted as WIRED, not dismissed because old summaries were wrong.
- **REPO-01:** source/license policy, all ten native source headers, actual header-only bridge build, and the tracked native license gate have exit-0 evidence. The independent native CI job is structurally connected. No remote execution or changed native behavior is claimed for the header-only rebuild.
- **REPO-05:** corrected canonical clone and exact MCP list/read pass are real. INT-07 is a remaining clean-environment dependency gap, not a denial of those repairs.
- **WARN-01 — RLM/default-runner/manual messaging:** production default registry intentionally does not compose live-parent RLM or messaging. Enabling a flag alone does not supply a child runner/session store/live session context. Kernel construction defaults `run_child=None`; its no-runner error is not child delivery. Scripted child isolation and two manually registered messaging sessions must remain described at that scope.
- **WARN-02 — Rust/fixtures/CI:** retained upstream Rust diagnostic is **exit 101: 5089 passed, 2 failed, 19 ignored, 3 filtered**. The old 622 figure is partial fail-fast accounting, not full-workspace success. The three ACP exclusions are not the two ext4 failures. Six parity fixtures are source-derived at the pin, not a new executable Rust/Python differential oracle. Local actionlint/source checks prove configuration shape, not cloud build/test success; live external providers were not exercised.
- **WARN-03 — documentation:** `docs/connectors.md` and CHANGELOG still describe adapters between the tool surface and every capability, contrary to INT-01. `docs/migration.md` still claims bit-for-bit pre-v10 prompt behavior without the historical comparison. Generated `docs/tool-catalog.md:884+` marks default-disabled Prime tools 'Approval: not required' and 'Required params: none' because catalog rendering asks the disabled default registry for absent tools; registered writers such as `rlm_spawn` actually require approval and parameters. The runtime guard is authoritative, but these published metadata are not accurate enabled-family contracts.
- Linked-crate probes and native `prime_goal`/`prime_autonomous` helper state are not the full upstream SessionEngine/daemon or the same live stores/holders used by registered Python loop controls. No new native engine/daemon architecture is required or claimed by this audit.

### Requirements Integration Map

| Requirement | Integration Path | Status | Issue / evidence scope |
|---|---|---|---|
| DISC-01 | Capability map → cited pinned source contracts → later port/fixture provenance | WIRED | Documentation criterion; mapped capability existence does not prove execution |
| DISC-02 | Overlap map → registry/roster/assembly/loop/config/durability locations | WIRED | Exact integration points recorded; actual missing links reported separately |
| DISC-03 | Pin → VENDOR → recorded baseline and CI skip set | WIRED | Requirement explicitly records retained exit 101; 5089 total passes, not a green workspace |
| BUILD-01 | Pin → Rust CI checkout/toolchain → locked build/test steps | WIRED | Configured cloud path; no fresh remote pass claimed |
| BUILD-02 | Pinned workspace → license allowlist → recorded cargo-deny gate | WIRED | Historical upstream license pass; current native license gate is separately exit 0 |
| BUILD-03 | In-repo toolchain 1.98.1 → workflow inputs → actual current native build | WIRED | Local pin match; not evidence all cloud jobs ran |
| RLM-01 | Explicit runner → RLM tool/host spawn → child future → collect states/errors | WIRED | Scripted contract is explicitly required; default native child delivery excluded |
| RLM-02 | Host retained children → rostered list/delete → status/reap responses | WIRED | Explicit host consumers/tests; result-channel defect separately affects RLM-04 |
| RLM-03 | create_session → durable store/recovery; child note → parent snapshot | BROKEN | INT-02: empty touched file, unused store injection, unbound always-accepted kernel note |
| RLM-04 | Separate child input/context → parent result channels | BROKEN | Isolation receipt passes; INT-03: answers also returned by list/delete |
| HARN-01 | Registered CRUD → fresh local/global HarnessState → disk reload/read | WIRED | Persistent entries, not automatic dynamic prompt injection |
| HARN-02 | Registered refine → evidence filter → proposals/diff → persisted updates | WIRED | Current registered proof and implementation trace |
| HARN-03 | Pre-change snapshot → applied refinement → registered rollback → prior entries | WIRED | Actual before/after repair; audit trail retained intentionally |
| HARN-04 | Refine/rollback → two actual turns → unchanged base prompt bytes | WIRED | Current registered receipt, not only old prose |
| LOOP-01 | Registered goal tools → fresh store factory → loop accounting/continuation/stop | WIRED | Real Rust/local-SSE controls plus current suite |
| LOOP-02 | Registered heartbeat → cron/APScheduler → named lease/agent → saved outcome | WIRED | Actual named delivery, ownership, clear safety and shutdown receipts |
| LOOP-03 | Registered driver → turn boundary → budget/gate → honest authoritative stop | WIRED | Actual turn/token/time/gate/refusal evidence |
| LOOP-04 | Two explicit live session registries → rostered send → inbox → observe | WIRED | Manual in-process registration; no default automatic native messaging claim |
| LOOP-05 | Default-off config → registry and static roster/prompt | BROKEN | INT-04: registry filters, static roster/prompt do not |
| LOOP-06 | Live goal/driver/heartbeat hook → structured redacted event → bounded normal flow | WIRED | Actual repaired paths; provider errors/refusals keep their own semantics |
| LOOP-07 | Flags-off current loop → recorded pre-v10 transcript comparator | BROKEN | INT-05: current-v-current tests, no recorded historical fixture |
| CONN-01 | Tool consumer → typed versioned adapter → capability → response consumer | BROKEN | INT-01: five connector classes bypassed by real handlers |
| CONN-02 | Standalone typed request tests → real capability → typed response checks | WIRED | Adapter-level contract tests only; not production conformance |
| CONN-03 | Failure injection → actual adapter-consuming loop → structured recovery | BROKEN | INT-01: direct adapters/wrapper tests do not connect full raise/timeout/bad-payload consumer flow |
| CONN-04 | Six pinned source-derived fixture files → Python parity consumers | WIRED | Passing source-contract fixtures, not new Rust differential execution |
| REPO-01 | AGPL metadata/text/headers/attributions → Python/native source and license gate | WIRED | Current source-policy and header-only native build/license evidence |
| REPO-02 | Required root/workflow/template files → repository consumers | WIRED | File-set criterion; clean Python CI prerequisite gap is INT-07 |
| REPO-03 | ADR/connectors/loop/migration docs → GitBook navigation/link consumers | WIRED | Structure/link criterion; semantic overclaims remain WARN-03 |
| REPO-04 | Supply-chain config → Cargo/pip/actions updater and license/audit jobs | BROKEN | INT-06: Cargo updater absent; actual source-only Cargo resolution 101 |
| REPO-05 | README clone/install/setup/build/config/MCP → clean user environment | BROKEN | URL/install/MCP repairs pass; INT-07: quickstart full suite omits required pinned checkout |
| DONE-01 | All requirement-specific passing evidence → factual milestone audit | BROKEN | INT-08: unresolved requirements; archived blanket acceptance is insufficient |
| DONE-02 | Green audit → reopened STATE/ROADMAP/MILESTONES → archive/cleanup | BROKEN | INT-08: Phase 61 active; no current completion/archive/publication |

**Requirements with no operational cross-phase wiring:** DISC-01/DISC-02 are discovery-document criteria; REPO-01/REPO-02/REPO-03 are legal/static/documentation criteria; DONE-01/DONE-02 are administrative closeout criteria. REPO-02's file-presence portion is self-contained. Their artifacts can be consumed across phases, but passing them does not demonstrate a runtime user flow. CONN-02 and CONN-04 have test-level cross-phase consumers, not independently proved production adapter consumers.

**Disposition for the parent:** retain the exercised Phase 61 loop, harness, license, URL and MCP successes. Do not promote historical scripted contracts, source-derived fixtures, local checks, or helper probes into unexecuted default-native/cloud claims. Resolve or explicitly obtain user-approved changes to the broken criteria; no scope exception, milestone audit write, archive, or publication is authorized by this result.
