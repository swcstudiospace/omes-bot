---
phase: "61"
slug: prime-loop-gap-closure
status: repaired_verified
threats_open: 0
threats_total: 26
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-10-08
---

# Phase 61 — Security

The active verify hooks require Nyquist then security. Configuration is ASVS L1,
blocking threshold high. Original 01/02 evidence closed 15 plan threats; broader
integration reopened T-61-01 and added nine 03-06 threats; the independent review added
two high threats (messaging identity, tool-call argument integrity). All 26 are closed
with exercised evidence after the 2026-10-09 review-repair wave. This is not a signed
A10/A11 verdict or a deployed CI pass; it records two user-approved criterion exceptions.

## Trust boundaries

| Boundary | Data crossing | Control |
|---|---|---|
| Registry/tool dispatch → runtime bindings | Goal factory, live driver, heartbeat runtime | Registering families publish to their own registry; dispatch keeps policy/approval enforcement. |
| Model/tool result → continuation | Stored objective/step, real usage/verdict | One transcript/lease/journal/cap; per-call known budget charge; no new privilege or gate bypass. |
| jobs.json / scheduler → named runner | Session, prompt, schedule, result | Validate before persistence; identifiable malformed rows disarm; snapshots preserve runner/sink ownership; wait/callback outside bookkeeping lock. |
| Hook/beat failure → persisted history/event | Exception detail | Structured error and redacted owning sink; no repr success fallback; foreground provider errors retain propagation. |

## Threat register

| Threat | Category / severity | Disposition | Found mitigation and exercised evidence | Status |
|---|---|---|---|---|
| T-61-01 | Spoofing / medium | mitigate | Effective prompt and offered roster derive from family flags (`assemble.render(config)`, default-off canonical artifact; registry-served roster is roster intersect registration: 108 default tools, 0 Prime). Static roster YAML stays a documented superset (W-5). Exercised: assembler tests, `--enable-family ... --output`, MCP stdio 108 default / 136 with five families. | closed |
| T-61-02 | Tampering / medium | mitigate | Fresh goal factory and live holder at each boundary; external pause/clear/completion/budget regressions. | closed |
| T-61-03 | Tampering / high | mitigate | Model effects still traverse real registry dispatch. Actual approval-denied disk tool performs no effect; ordinary successful denial prose is not misclassified. | closed |
| T-61-04 | DoS / high | mitigate | Existing cumulative model-call cap and nonrefilled caller budget; sticky stops; degraded hook cannot extend. Actual native turn/token/time limits and gate outcomes. | closed |
| T-61-05 | DoS / medium | mitigate | Foreground fast-fail unchanged; beat waits opt-in outside bookkeeping lock. Actual two-session lease overlap/reentrant tools and controlled drain regressions settle. | closed |
| T-61-06 | Disclosure / high | mitigate | Guarded/redacted hook events, actual malformed/HTTP-error history and per-session sink isolation; no secret leakage or implicit retry. | closed |
| T-61-07 | Privilege / low | mitigate | User-role continuation grants no tools or approvals. Same denied-effect proof; no newly accepted risk. | closed |
| T-61-SC | Tampering / low | mitigate | No new product dependency/version in this slice. Current lockfile pip audit and native license graph exit 0. cargo-deny install is a verifier tool, not a product dependency. | closed |
| T-61-02-01 | Tampering / medium | mitigate | Session/prompt, finite due/interval, calendar bounds and advancing deadlines validated before writes. Actual tiny interval rejection leaves disk unchanged. | closed |
| T-61-02-02 | Tampering / medium | mitigate | Whole-file corruption / owned missing identity raises. Other malformed/foreign rows isolated; identifiable malformed heartbeat disarms after one diagnostic, valid neighbors run. | closed |
| T-61-02-03 | DoS / medium | mitigate | Per-job claim/in-flight guard, coalescing/max-instance behavior and bounded history. Actual two-second stall resumes exactly one persisted beat. | closed |
| T-61-02-04 | Disclosure / medium | mitigate | Captured owning sink redacts callback/serialization errors; actual Alpha HTTP 400 cannot reroute to Beta; no raw repr persistence. | closed |
| T-61-02-05 | Spoofing / low | mitigate | Unknown session/id fail explicitly, never create conversations. Existing consumer regressions; no risk acceptance. | closed |
| T-61-02-06 | Tampering / medium | mitigate | Only owned backend entries are pruned; actual injected foreign entry preserved; dead injected executor cannot restart silently. | closed |
| T-61-02-07 | Privilege / medium | mitigate | Atomic expected-runner detach and captured runner/sink pair; stale close preserves replacement, later explicit stop defeats stale restart; real named-session and deterministic lifecycle evidence. | closed |
| T61-INT-TYPE | Tampering / high | mitigate | Every registered tool of seven families (37) decodes through a versioned typed request before any effect; undeclared keys, bad versions and malformed argument JSON never run a tool. Exercised: mechanical 37-tool proof over registry and stdio MCP, `test_prime_*_surface/boundary`, `test_prime_loop_boundaries.py`, probe 17 defects before / 0 after. | closed |
| T61-INT-AUTH | Privilege / high | mitigate | Policy then approval precede decode in every family; typed failures are audited `error`, denials `denied`; bindings grant nothing. Exercised: `test_prime_tool_authorization.py` (7 families x policy/approval/typed/valid), kernel rejected requests import nothing and write nothing. | closed |
| T61-RLM-DURABLE | Tampering / high | mitigate | Atomic versioned child documents, recovery without replay, explicit interrupted-error status, explicit parent contract (`require_parent`, no cwd default), recovery that survives a write failure, two-lock atomic admission. Exercised: `test_rlm.py` (real agent parent, recovery, concurrency), checker flow with a fresh host. | closed |
| T61-RLM-NOTE | Spoofing / high | mitigate | Child-bound note ownership and 10 s throttle; root or spoofed ids refused. Exercised: kernel host tests and the checker kernel flow (accepted then throttled, root note rejected). | closed |
| T61-RLM-CHANNEL | Disclosure / high | mitigate | Metadata-only list/delete across tools and kernel; answer only through settled collect; delete tombstones keep no prompt or answer. Exercised: `test_rlm.py`, `test_prime_kernel_host.py`, checker flows (no answer text in list or delete). Residual: answers remain in the child session file under session_dir (W-6, documented). | closed |
| T61-PROMPT-FLAG | Privilege / medium | mitigate | Disabled family names are absent from the assembled prompt and from the served roster. Exercised: assembler/shell tests, `assemble-prompts.sh --check`, MCP stdio default 0 Prime tools. | closed |
| T61-CATALOG-POLICY | Privilege / medium | mitigate | Catalog metadata comes from real registrations (`full_inventory_registry`), true approval flags and required fields. Exercised: `tooling.catalog --check`, catalog tests, checker enumeration of all 37 Prime tools. | closed |
| T61-GOLDEN-ORIGIN | Tampering / medium | mitigate | Six transcripts captured by executing immutable pre-v10 commit 79ff51af; current comparator passes and the checker re-proved 6/6 against a pristine checkout. The unmodified historical suite is 376 passed / 2 failed (inventory pins), a user-approved criterion exception (2026-10-09); no test edited or shimmed. | closed |
| T61-CI-PIN | Tampering / high | mitigate | Python CI and README provision the contract pin before the suite. Exercised: fresh venv install of the working tree with the pinned public checkout, 949 passed / 13 skipped, setup_check 0 (local snapshot; no cloud CI observed). | closed |
| T61-MSG-IDENTITY | Spoofing / high | mitigate | Messaging identity is bound to the registering session; undeclared keys (`sender`, `session`, `mark_read`) are `unknown_field` and never merged. Exercised: real-agent tests (cross-session read and sender forgery rejected, inboxes untouched), checker forged-sender flow. (Found by the independent review as CR-01.) | closed |
| T61-LOOP-ARGS | Tampering / high | mitigate | A malformed or non-object tool-call argument payload is an `error:` row and the tool is never called (only None/empty string mean no arguments). Exercised: `test_prime_loop_boundaries.py`, probe (truncated, list, null before/after). (Found by the independent review as CR-02.) | closed |

## Accepted risks log

Accepted by the user on 2026-10-09 (explicit, not inferred):

- **REPO-04 exception — no Cargo Dependabot.** The Cargo path dependencies live in the
  ignored read-only prime-agent checkout, so Dependabot cannot resolve them (source-only
  `cargo metadata --locked` exits 101). Residual risk: Cargo dependency updates for the
  parity-oracle workspace are not automated; cargo-deny (licenses/advisories) and pip-audit
  run, and pip and github-actions Dependabot are configured.
- **LOOP-07 exception — unmodified historical suite.** 376 passed / 2 failed (catalog/roster
  inventory pins) before and after the repair wave; flags-off behavior is proven by 6/6
  captured pre-v10 transcripts.
- **CONN-01 documented scope.** Loop-internal goal accrual and driver consult use the live
  store/driver with typed response views; the kernel wire ignores undeclared SDK kwargs.

The pre-existing PYSEC-2026-4114 exception remains exactly the documented oauthlib
server-PKCE scope in root SECURITY.md and the supply-chain workflow. No new advisory or
architecture waiver is accepted here.

## Audit trail

| Date | Threats total | Closed | Open | Owner |
|---|---:|---:|---:|---|
| 2026-10-08 | 15 | 15 | 0 | Parent integration owner; plan register + current source/behavior proof |
| 2026-10-09 | 26 | 26 | 0 | Parent integration owner; independent post-repair review (0 open), final 32-ID integration check, mechanical typed-boundary proof |

## Evidence and limits

Final tree: 980 tests, 26 evals, Ruff, format and mypy (245 sources), assembled-prompt, catalog
and setup checks pass. The independent post-repair review (`61-REVIEW.md`) has no open
findings; the final integration check (`61-INTEGRATION.md`) proved the typed request boundary
on all 37 registered Prime tools. Earlier native/Anthropic gate, delayed-scheduler,
provider-error/redaction and approval-denial receipts are retained in `61-EVIDENCE.json`.
Not observed: cloud CI, upstream Rust test reruns, a published-clone run. See
`61-EVIDENCE.json#review_repair_wave` and `.planning/v10-MILESTONE-AUDIT.md`.

REPO-04 is a user-approved criterion exception (2026-10-09), not a closed supply-chain
automation requirement. No remote CI, credentialed external service, native engine/daemon,
or upstream Rust test rerun is claimed. The retained vendor Rust exit-101/ext4 baseline
remains explicit.

## Sign-off

- All 26 register threats have found mitigations with exercised evidence; `threats_open: 0`.
- ASVS L1 verified against the plan-authored register plus the two threats added by the independent review.
- No automatic risk acceptance or signed specialist verdict fabricated; the three exceptions above were accepted by the user.
- Phase behavior is verified; the milestone lifecycle stays open (REPO-05, DONE-01, DONE-02).

## Security Audit 2026-10-08

| Metric | Count |
|---|---|
| Threats found | 15 |
| Verified | 15 |
| Accepted | 0 |
| Open | 0 |

## Expanded gate after exact integration audit (2026-10-08, closed 2026-10-09)

The 15/15 audit above is the original 01/02 snapshot. The expanded register had 24 threats
(14 closed / 10 open: one reopened original and nine plan-authored risks). Plans 61-03..06
and the review-repair wave closed each with integrated source and actual consumer evidence;
the independent review then added T61-MSG-IDENTITY and T61-LOOP-ARGS, both repaired and
exercised.

## Security Audit 2026-10-09

| Metric | Count |
|---|---|
| Threats found | 26 |
| Verified | 26 |
| Accepted risks (user, explicit) | 3 exceptions/scope decisions (REPO-04, LOOP-07, CONN-01) |
| Open | 0 |
