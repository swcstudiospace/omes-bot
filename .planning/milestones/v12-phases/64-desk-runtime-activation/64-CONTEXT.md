# Phase 64 Context: Desk runtime activation

**Milestone:** v12 Programming Desk merge. **Source:** `/root/src/repos/programming-desk`
@ `9de3aa3` (seven-seat desk OS). **Seeds:** SEED-005, SEED-014.
**Evidence base:** read-only scout audits of both repos (2026-10-09), full reports at
`agent://DeskSourceMapper` and `agent://OmegaSeamMapper` (session transcript history).

## What SEED-005 claimed vs what the tree shows (8/8 CONFIRMED-GAP)

1. **Empty desk seams.** `omega_prime/mcp_server.py:206` builds `LeadClient(LeadContext(root=root))`
   only; `mcp_server.py:215-217` build `MobileContext(root=root)`, `InfraContext()` (no args),
   `QualityContext(root=root)`. `LeadContext` optionals all default `None`
   (`omega_prime/tools/lead.py:289-304`), so `lead_docs_search`, `lead_memory_*`,
   `lead_intake_next/ack`, `lead_graph_*`, `lead_bus_*` return
   `not_configured` (`lead.py:355-359,390-395,599-600,742-743,767-768,817-818,870-871,913-914,539-540`),
   `lead_event_emit` degrades silently (`lead.py:637-639`), `lead_brief` shows empty
   packs/intake (`lead.py:331-332`), and `lead_doctor` is red on memory/tools/substrate
   (`lead.py:717-731`) — which is why `omega_prime/grokbot/templates/OMEGA_PRIME.md:65` keeps
   the desk routine "paused until lead_doctor is green".
2. **Coding tools jailed to the install tree.** `mcp_server.py:176` passes
   `root / "omega_prime"` to `register_coding_tools`; the file jail is
   `omega_prime/tools/file_ops.py:39-42,159-184`; cwd defaults in
   `omega_prime/tools/coding.py:66,73`; LSP/DAP spawn with `cwd=str(root_path)`
   (`omega_prime/tools/ide.py:52-57,82-86`). `root` also locates roster/policy/prompts/
   ownership (`mcp_server.py:521-535`; `lead.py:432,487`; `quality.py:242`) — install root and
   work root must be split.
3. **`delegate_task` not served.** Registered nowhere in production: `mcp_server.py:129-131`
   ("Delegate needs a live agent: skipped") and `mcp_server.py:242-247`; rostered at
   `omega_prime/contracts/tool-rosters/omega-prime.yaml:48`, allowed at
   `omega_prime/contracts/policies/omega-prime.json:22`; excluded by
   `omega_prime/setup_check.py:80-103`, asserted absent in
   `omega_prime/tests/test_mcp_server.py:130-141`, classified live-agent-only by
   `omega_prime/grokbot/doctor.py:43-53`. The 108 served = 146 rostered − 37 default-off
   `prime.*` − `delegate_task`.
4. **Lead pass test-only.** `omega_prime/routines/desk_lead.py:20-113` takes an injected
   `dispatch` callable (`None` ⇒ every ticket blocks "no dispatcher", `desk_lead.py:44-49`);
   called only from `omega_prime/tests/test_desk_lead.py`. No cron/heartbeat/loop wiring;
   intake tools fail `not_configured` anyway (claim 1).
5. **Gates self-referential.** `omega_prime/tools/quality.py:148-176`: `qua_gates_run` takes
   no arguments and hardcodes `pytest omega_prime/tests`, the evals runner and
   `assemble-prompts.sh --check` with `cwd=ctx.root` (the Omega Prime checkout).
6. **Receipts self-attested; self-approval deadlock.** `omega_prime/receipts.py:11-101`
   validates only the shape of model-typed text (no re-execution, no exit-code truth);
   destructive receipts refuse `approved_by == bot` (`receipts.py:96-101`) and
   `qua_receipt_approve` refuses `bot == QualityContext.bot_id`
   (`omega_prime/tools/quality.py:251-252`) — with a single identity (`bot-00-omega-prime`,
   `lead.py:292`, `quality.py:139`) nothing can approve anything.
7. **Five service clients absent.** `InfraContext.railway=None` (`omega_prime/tools/infra.py:53-60`;
   four `infra_railway_*` tools → `not_configured`, `infra.py:76,150,183,197`),
   `QualityContext.greptile=None` (`quality.py:131-139,196-200`),
   `WebContext.vercel/browser_factory=None` (`omega_prime/tools/webpack.py:57-68,447-452`),
   `PlaywrightBrowser` factory never wired (`omega_prime/tools/browser_egress.py:1634-1648`
   constructed only in tests), `MobileContext.play/asc=None`
   (`omega_prime/tools/mobile.py:107-117,628-647`). Credential broker providers are LLM-only
   (`omega_prime/credentials/broker.py:17-49`).
8. **No desk config surface.** Only `prime.*` flags exist (`omega_prime/config.py:31-43,46-69`);
   desk packs always register with empty seams (`mcp_server.py:176-238`); host deploy uses the
   same registry (`omega_prime/grokbot/deploy.py:217`, `oneclick.py:557`, `supervisor.py:44`);
   `grokbot/rosters/default.json:8-23` carries `absorbed_seats` metadata that no code consumes;
   `grokbot/manifest.py:322-324` hardcodes `programming_desk: true`.

## Source pattern to preserve (programming-desk @ 9de3aa3)

- **Receipt contract** (PD `prompts/_shared/core-directives.xml:122-155`, G-2
  `ci/gates/check_receipt.py:26-743`): commands with real exit codes; claims citing command
  indexes; `expects_failure` parity; 19 bypass patterns; self-approval refused
  (`approved_by` missing or == bot); `loop_acks` separate from `approvals[]`; vague
  `unverified` rejected. Live sample: `.receipts/bot-01-systems-backend/desk-v8.3-workbench-traceability.json`.
- **Ownership** (`ownership.yaml:2-13`, `check_ownership.py:36-72`): glob rules, last match
  wins, unowned path = failure, `contract_surface` flag.
- **Gates as executables** (`ci/gates/run_all.py:26-82`): G-1..G-7 sequence, exit 1 if any
  gate failed, "never bypass a gate".
- **Intake state machine** (`store.py:17,108-135`): queued|claimed|accepted|rejected|
  in_progress|done|dead_letter, per-origin idempotency, DLQ.
- **Roster model** (`rosters.py:51-162`): seat = core + own tools (band 10-15), packs ≤ 5
  tools each, live ceiling 20, per-tool `kind`/`gates` fields (g5 ⇒ rollback_plan+approval_id
  required, g6 ⇒ approval_id).
- **Desk loop** (`docs/desk-operating-model.md:23-39`): intake → uplift → dispatch →
  implement in owned paths → receipt → QUALITY → consolidate → report.

## Merge decisions for this phase (from the user's direction + recorded decisions)

- One bot (`bot-00-omega-prime`) controls subbots: the absorbed seats stay tool packs; the
  lead pass dispatches subagents through `delegate_task`/RLM — no second gateway process.
- Behavior-port, no new third-party dependencies (v10/v11 precedent); no env changes required
  for default operation; everything degrades loudly without credentials.
- Substrate mediation stays; Tailscale forwarders default network path; no Railway resource
  changes (user decisions 2026-10-07, `.planning` research artifacts).
- Install root vs work root split is additive: default work root = install root (today's
  behavior unchanged); Grok Bot attach gains an explicit work-root option.
