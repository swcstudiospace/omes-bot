---
milestone: v10
name: Prime merge — reopened existing-gap closure
audited: 2026-10-09
status: gaps_found
scores:
  requirements: 22/32
  integration: 9/17
  flows: 9/17
requirement_disposition: scoped-wiring-not-blanket-cloud-pass
active_phase: 61
---

# v10 milestone audit — factual current continuation gate

**Closeout blocked.** Exact independent gsd-integration-checker accounts for all32 IDs:22WIRED/10BROKEN, nine complete scoped flows and eight broken acceptance flows. This is the pre-repair cross-phase gate; current03–06 edits are not promoted to an unrun new pass. Historical53–60 archives stay frozen. No milestone completion/archive/cleanup/publication is performed.

## Requirement-by-requirement integration and evidence

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

## Actual command receipts and evidence scopes

| Evidence | Actual command/scenario | Exit/result | Scope |
|---|---|---|---|
| P1 | `.venv/bin/python -m pytest omega_prime/tests -q` |0;686passed/12warnings | Last completed original01/02 snapshot; does not clear missing literal criteria or current in-flight edits |
| P2 |15-file affected pytest command retained in61-EVIDENCE.json |0;234passed | Existing loop/scheduler/refine/license/docs regressions |
| P3 | `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` |0;26passed | Hermetic evals, not live external services |
| P4 | Ruff/format/mypy, assembly/catalog/setup, actionlint and lockfile pip-audit commands retained in61-EVIDENCE.json | Final post-retirement exits0 | Applicable recorded static/source/config snapshot; one pre-existing explicitly approved advisory ignore only |
| P5 | Locked current native wrapper build and license commands retained in61-EVIDENCE.json |0 /0 | Header-only native/license work, not a new native engine or all-crate behavior |
| P6 | Retained upstream workspace baseline in VENDOR/53 records |101;5089passed/2failed/19ignored/3filtered | RequirementDISC-03 records diagnosis; never relabel a green Rust workspace or rerun known ext4 failures |
| P7 | Real native/local-SSE controls and scheduler, registered refine/rollback/fixedprompt, explicit scripted child isolation and exact stdio MCP list/read | Actual exits0 retained | Nine traced scoped flows; no default native child or automatic native messaging claim |
| N1 | Actual registered-tool/RlmHost/kernel/render before smoke |0 diagnostic;boolean admitted, list answer leak,0-byte session,0 recovered, unbound notes accepted, disabled name shown | Demonstrates violations, NOT a requirement pass |
| N2 | Isolated actual Python source layout without ignored Prime checkout |0 diagnostic;missingCargo.toml and missingrlm imports reproduced | Clean prerequisite failure is observed, not merely inferred; not a full isolated suite |
| N3 | Complete source-only Cargo resolution command |101;required ignoredcrossterm manifest absent | Cargo updater absent; no packaging exception authorized |
| H1 | Immutable79ff51af historical source execution of retained capture_script |0;six full consumer transcripts/effects/approval/stop/call counts | Actual imported pre-v10 source origin observed; current comparison remains pending integrated wave |
| N4 | Actual delivered kernel/persistence diagnostic after first Plan04 edit |0 diagnostic;kernel boolean stilladmitted, forged unbound note accepted, collectdone while diskrunning, freshhost0children | Returned to same execution owner; not silently waived |

## Reopened criterion ownership and next safe actions

- **INT-01** — CONN-01, CONN-03: Typed connectors and their failure-injection tests are not connected to production consumers.
- **INT-02** — RLM-03: Durable child-session persistence and child-to-parent progress delivery are missing.
- **INT-03** — RLM-04, CONN-01: Child answers are exposed through list/delete as well as collect.
- **INT-04** — LOOP-05: Disabled families remain in the static roster and assembled prompt.
- **INT-05** — LOOP-07: There is no recorded pre-v10 transcript fixture comparison.
- **INT-06** — REPO-04: Cargo Dependabot is absent and required Cargo paths are not repository-fetchable.
- **INT-07** — REPO-05, DONE-01: Clean-clone quickstart and Python CI omit the checkout required by unconditional kernel tests.
- **INT-08** — DONE-01, DONE-02: Complete factual audit and reopened milestone closeout remain blocked.

- Plans61-03/04/05 write disjoint existing Python typed-consumer/RLM/prompt/catalog slices. Parent61-06 final current comparator, isolated checkout/full suite, exact composition and docs depend on allthree.
- Original phase-only5/5 truths/7loop claims are retained as narrow observations, contradicted where the stronger32-ID gate names a literal consumer/fixture criterion. No inherited checkbox overrides actual violations.
- Actual pre-v10 commit79ff51af41e2469b906a501814d1899a13be9679 is the observed direct parent of first v10 commit70babccf; not the earlier rename commit or an invented v9-final tag. Fixture JSON preserves actual old output and source/script provenance; no expected output copied from current code.
- Expanded24-threat register has14closed/10open (one original reopened +nine new). Updated Nyquist/security/review and exact integration gates follow real integrated smoke. No signed A10/A11 or cloud-CI result fabricated.
- REPO-04 decision is material: repository-fetchable pinned sources (read-only gitlink/submodule is a primary-source-supported candidate, not yet proven) versus a user-approved criterion exception. No decision inferred from genericcontinue; no Cargo YAML no-op.
- DONE-01 cannot pass while any original criterion is unmet/unapproved. DONE-02 requires factual authorized current lifecycle/archive/cleanup; historical archives are not new completion. Preservation/preview and user confirmation gates remain intact.

## Evidence provenance

Current machine receipts/sources: `phases/61-prime-loop-gap-closure/61-EVIDENCE.json`. Exact read-only integration report: `phases/61-prime-loop-gap-closure/61-INTEGRATION.md`. Plans/context/validation/security records are active under the same phase. Archived milestone audit/SUMMARY/VERIFICATION records are inherited historical evidence with missing legacy SUMMARY requirements metadata, not fabricated three-source coverage. The current32-row mapping above is complete, including negative dispositions; this gaps_found audit is not a passing milestone audit.
