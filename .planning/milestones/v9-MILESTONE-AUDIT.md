---
milestone: v9
milestone_name: SOTA upgrade
audited: "2026-10-08"
status: passed
scores:
  requirements: 19/19
  phases: 7/7
  integration: 5/5
  flows: 5/5
implementation:
  completed_plans: 12
  total_plans: 12
security:
  asvs_level: 1
  block_on: high
  threats_total: 32
  threats_closed: 32
  blocking_open: 0
  accepted_risks: []
nyquist:
  compliant_phases: [46, 47, 48, 49, 50, 51, 52]
  partial_phases: []
  not_validated_phases: []
  missing_phases: []
  overall: compliant
gaps:
  requirements: []
  integration: []
  flows: []
  security: []
tech_debt:
  - phase: "46-land-hardening"
    items: ["Screenshot-name sanitization is duplicated in mobile.py and webpack.py; not the blocking SSRF control gap."]
  - phase: "50-provider-protocols"
    items: ["Responses streaming/reasoning continuity remains explicitly deferred; chat streaming and current Responses routing are implemented."]
  - phase: "51-redteam-depth"
    items: ["macOS appdirs ignores XDG_DATA_HOME; Linux isolation is verified, macOS behavior is not certified."]
  - phase: "milestone"
    items: ["Final suite emits 12 existing audioop/PyRIT deprecation warnings."]
closure:
  authorized: true
  reason: "All 19 v9 requirements satisfied. SEC-NET 2.2.0 egress transport and browser boundary hardening implemented and verified. Real Python 3.12, 3.13, and 3.14 matrix execution verified."
---

# v9 — Milestone Audit

**Verdict: passed.** Phase 46 egress hardening, Phase 48 Python 3.12-3.14 matrix, and all milestone phases 46-52 are complete and verified.

## Scope and evidence provenance

- All seven implementation plans already have summaries. Existing Phase 46–51 execution history was resumed, not rerun wholesale.
- Interrupted Phase 52 work was completed: sanitized chunk-only docs answers, real approval-sensitive ultrathink evals, truthful docs/catalog, and all five original review findings closed.
- Historical body-only summary/verification records were normalized for canonical discovery without inventing fresh execution receipts. Current continuation receipts and expanded per-requirement evidence remain separately identified.
- Independent reviewers: `Phase52ReReview` reviewed 13 changed paths; parent reviewed three audit-cleanup test paths. `Phase52GoalGate` verified the Phase 52 goal. `V9CoverageIntegration` mapped cross-phase behavior. `V9SecurityGate`, a read-only security specialist, supplied retroactive STRIDE evidence; parent integrated security artifacts and enforced the gate. The named GSD security-auditor agent was unavailable; this role adaptation is explicit.
- Source-control policy remains unchanged: no commit, push, merge, tag, installed-GSD edits, or phase-directory archival. Existing dirty/untracked work is preserved.
- No live provider, substrate, ultrathink, browser attack, or external SQL probe was run. Read-only GitHub run inspection was performed solely to look for matrix evidence.

## Phase gates

| Phase | Original plans | Current verification | Nyquist | Security | Closure readiness |
|-------|----------------|----------------------|---------|----------|-------------------|
| 46 — Land hardening | 1/1 implemented | gaps_found | partial | 10/12 closed; two high open | blocked |
| 47 — Lint/types | 1/1 implemented | passed | compliant | 2/2 closed, scoped L1 | ready |
| 48 — Dependencies/matrix | 1/1 implemented | human_needed | partial | 3/3 closed, scoped L1 | actual matrix validation required |
| 49 — Provider resilience | 1/1 implemented | passed | compliant | 3/3 closed, scoped L1 | ready |
| 50 — Provider protocols | 1/1 implemented | passed | compliant | 4/4 closed, scoped L1 | ready |
| 51 — Red-team depth | 1/1 implemented | passed | compliant | 3/3 closed, scoped L1 | ready |
| 52 — Answers/evals/docs | 1/1 implemented | passed | compliant | 5/5 closed, scoped L1 | ready |

Canonical `init.manager` reports five complete phases and `all_complete: false`. Original plan completion is not equivalent to passing current milestone gates. The active `verify:post` hooks resolve to `validate-phase` and `secure-phase`, both with `onError: halt`.

## Requirements — three-source cross-reference

Sources: current `REQUIREMENTS.md` traceability/checkboxes; each phase's expanded current verification requirements table; each `*-SUMMARY.md` `requirements-completed` list, cross-checked against its plan declaration. Summary claims are historical execution claims, not automatic acceptance. Current per-requirement evidence keeps unaffected LAND-02 satisfied while the Phase 46 security gate remains blocked. LAND-01 is unsatisfied at acceptance despite partial implementation; HYG-05 needs human validation. No orphaned v9 requirement was found.

The source stem identifies the PLAN/SUMMARY pair in the corresponding phase directory.

| Requirement | Source stem | Summary claims complete | Current requirement checkbox | Current verification evidence | Audit result |
|-------------|-------------|-------------------------|------------------------------|-------------------------------|--------------|
| LAND-01 | 46-01 | yes | unchecked / partial | two high SSRF controls/regressions missing | unsatisfied |
| LAND-02 | 46-01 | yes | checked | composition/assembly/setup/catalog green | satisfied |
| HYG-01 | 47-01 | yes | checked | actual Ruff lint clean; CI gate declared | satisfied |
| HYG-02 | 47-01 | yes | checked | actual Ruff format check clean; CI gate declared | satisfied |
| HYG-03 | 47-01 | yes | checked | actual mypy zero errors; CI gate declared | satisfied |
| HYG-04 | 48-01 | yes | checked | floors/committed lockfile; current pip consistency | satisfied |
| HYG-05 | 48-01 | yes | unchecked / partial | actual 3.12 passes; real matrix/3.13+ outcomes unverified | partial |
| HYG-06 | 48-01 | yes | checked | v2 contract and actual SDK schema/error behavior | satisfied |
| PCUR-01 | 49-01 | yes | checked | current retry/backoff behavior suite | satisfied |
| PCUR-02 | 49-01 | yes | checked | provider usage reaches conversation-loop spans | satisfied |
| PCUR-05 | 49-01 | yes | checked | configured defaults/docs updated; no live model certification | satisfied |
| PCUR-03 | 50-01 | yes | checked | Responses/chat routing and fallback behavior | satisfied |
| PCUR-04 | 50-01 | yes | checked | streamed output reaches the conversation loop | satisfied |
| DPT-01 | 51-01 | yes | checked | Linux PyRIT isolation receipts and current isolated suite | satisfied |
| DPT-02 | 51-01 | yes | checked | deterministic orchestrator campaigns/turn chaining | satisfied |
| DPT-03 | 51-01 | yes | checked | scorer/objective verdict behavior | satisfied |
| DPT-04 | 52-01 | yes | checked | decoder → registry → MCP/next-model safe chunks | satisfied |
| EVAL-01 | 52-01 | yes | checked | production mark approval sensitivity and deny-by-default cases | satisfied |
| EVAL-02 | 52-01 | yes | checked | setup/defaults/catalog current; executable catalog gate | satisfied |

## Blocking security findings

### T-46-08 — Fetch destination enforcement (high)

`omega_prime/tools/webpack.py:71-106,224-229` checks literal spelling but accepts unresolved/noncanonical hosts, then delegates real resolution/connection to urllib. `omega_prime/mcp_server.py:161` leaves the shipped host allow-list unset. Existing canonical-literal tests do not prove DNS destination or connected-peer enforcement.

**Required:** validate all resolved A/AAAA destinations, reject non-public/ambiguous numeric forms, constrain the actual peer against rebinding, enforce the real fetch consumer's network policy, preserve no redirects, and add hermetic refusal regressions.

### T-46-12 — Browser requests escape the initial guard (high)

`omega_prime/tools/webpack.py:287-304` performs a guarded probe before separate browser navigation. `omega_prime/tools/playwright_browser.py:37-56` does not enforce destination policy on redirects, frames, subresources, or subsequent navigation.

**Required:** enforce destination/peer policy for every browser request, or require enforced egress sandboxing, with independent hermetic request-refusal regressions.

Both are source-observed missing controls. Private-service reachability/exploitation is **[INFERENCE], not exercised**. See [46-SECURITY.md](phases/46-land-hardening/46-SECURITY.md) for the register, exact evidence, and pending user disposition. The auditor cannot accept risk.

## Required matrix validation

Phase 48 success criteria explicitly require the suite to run on Python 3.12/3.13/3.14 and the Discord guard/suite to work on real 3.13+ interpreters. Only actual 3.12 execution was observed in this continuation; the historical audioop simulation is not sufficient.

- Executable lookup found no 3.13/3.14 on PATH. Narrowed standard/tool-cache discovery found only 3.12 binaries, including the actions-runner 3.12.14 cache; no alternative 3.13/3.14 runtime was discovered.
- Read-only recent branch-run inspection showed pre-v9 runs. Exact `gh run list --repo swcstudiospace/omega-prime --commit 36fd803c7b7c727e04edad2294f1e3cb800b0901 --limit 5 --json databaseId,headSha,status,conclusion,workflowName` returned `[]`.
- The final v9 tree includes uncommitted Phase 52 changes; no current-tree hosted CI proof is claimed. No workflow trigger, installation, or Git publication was performed.

Obtain actual runtime/matrix proof, or request explicit user approval to defer this named acceptance. No silent scope reduction. See [48-VERIFICATION.md](phases/48-deps-matrix/48-VERIFICATION.md) and [48-VALIDATION.md](phases/48-deps-matrix/48-VALIDATION.md).

## Cross-phase integration and flows

The integration review found no broken production call graph among five mapped boundaries. Phase 52's initial reviewer handoff marked docs integration partial because it belonged to the separate goal gate; the final goal verdict and actual consumer smoke resolved that ownership handoff. Matrix wiring is intact, but its required hosted/real-runtime execution remains unverified. Thus integration wiring is 5/5; exercised/accepted flows are 4/5, not 5/5 runtime proof.

| Flow | Wiring | Current behavior evidence | Flow verdict |
|------|--------|---------------------------|--------------|
| Provider retry/usage/routing/stream → loop | intact | current behavioral suite, including streamed loop consumption | satisfied, hermetic |
| PyRIT isolation → campaign → scorer verdict | intact | current campaign/isolation/scorer suite and keyless evals | satisfied, Linux/hermetic |
| Docs decoder → registry → MCP → next-model request | intact | actual production decoder/dispatch/MCP/loop smoke; secrets/raw fields absent | satisfied, hermetic |
| Real mark registration → approval/seat policy → handler | intact | actual registration evals; approval-removal sensitivity; empty-policy refusal | satisfied, hermetic |
| Catalog/setup/assembly → declared CI matrix gates | intact | local commands pass; real required 3.13/3.14 outcomes absent | human_needed |

## Exercised continuation verification

Final post-cleanup parent commands, in a fresh isolated HOME/XDG sandbox:

| Gate | Observed result |
|------|-----------------|
| `.venv/bin/python -m pytest omega_prime/tests -q -p no:cacheprovider --basetemp <sandbox>/pytest` | 344 passed, no skips; 12 warnings |
| `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` | 26 passed, zero failed |
| `bash omega_prime/scripts/assemble-prompts.sh --check` | up to date |
| `.venv/bin/ruff check omega_prime/` | clean |
| `.venv/bin/ruff format --check omega_prime/` | 205 files accepted |
| `.venv/bin/mypy --cache-dir <sandbox>/mypy omega_prime/` | zero issues in 174 files |
| `.venv/bin/python -m omega_prime.setup_check --root .` | roster/template/assembly OK; 108 MCP-served tools |
| `.venv/bin/python -m omega_prime.tooling.catalog --check` | catalog current |
| `.venv/bin/python -m pip check` | no broken requirements |

The earlier actual `SubstrateClient` MCP JSON decoder → `ToolRegistry` → `call_tool_handler` and `run_conversation` next-`ScriptedModel`-request smoke passed with zero live service calls: no raw retrieval, supported synthetic secret/sentinel absent, bounded typed metadata/citation provenance, strict-JSON finite scores, malformed-versus-empty distinction, and bounded/redacted errors. Runtime code was unchanged by subsequent test-only cleanup, so this remains applicable; it is not presented as a newly rerun smoke.

Ten inherited source/config/default-copy proxies were removed rather than re-pinned. The 354→344 test-count change is test cleanup, not narrowing behavioral regression coverage. Existing substantive docs navigation, Discord unavailable-import behavior, retrieval/MCP regressions, and approval sensitivity remain green.

Phase 52 canonical verification includes PLAN + SUMMARY + 15 current product/test/doc inputs (17 total), with fingerprint `v1:sha256:447e681f3d0f096c735491fb94ea75244f3a7a977d28e40176616ac1000c4f40`.

## Limits and deferred scope

Security closure is scoped retroactive ASVS L1/source/runtime evidence, not OWASP certification, CVE scanning, or proof of arbitrary PostgreSQL read-only semantics. The shipped SQL adapter is unconfigured; its lexical guard is not certified as a general database security boundary. No macOS isolation, fresh installation on every supported runtime, hosted matrix, keyed provider, or external-service certification is implied.

Documented debt: duplicated screenshot-name helper (46); Responses streaming/reasoning continuity (50); macOS XDG behavior (51); 12 pre-existing deprecation warnings. Future `TOOLC-01/02` and `DEEP-01/02/03` are explicitly v10/out of scope, not orphaned v9 requirements.

## Disposition and resume

Security choice: scoped remediation/retry (recommended), explicit acceptance of **both** named high risks, or stop. Matrix choice: obtain actual validation or explicitly approve deferral of that acceptance. No choice has been made. No phases or risks were silently skipped or waived.

`STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`, phase verification/validation/security artifacts, and the SDK waiting signal preserve these gates. Resume from this audit; do not rerun completed historical plans wholesale. Do not invoke milestone completion, tag/archive, or phase cleanup while unresolved gates remain. Archival/moving phase directories requires separate user confirmation even after gates are resolved.
