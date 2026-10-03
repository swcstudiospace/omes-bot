# Structure: desk inventory → Omes landing zones

## Gateway tools by seat file (61 total)

- `core` (9 +2 helpers): brief, docs_search, memory_retain/recall,
  ownership_resolve, receipt_check, event_emit, doctor, render_prompt
- `lead` (7): intake_next/ack, graph_register/state, bus_start/wait_job,
  roster_status
- `web` (5): vercel_deployments/promote/rollback, preview_check,
  bundle_secret_scan
- `mobile` (10): play_track_status/staged_rollout/halt_rollout,
  testflight_status, appstore_phased_release/pause_release,
  artifact_size_delta, lint_baseline_diff, entitlements_diff, review_risk_check
- `systems` (6 +1 helper): index_query, events_query, cache, lsp_diagnostics,
  contract_propose, design_artifact_get
- `infra` (7 +1 helper): railway_status/logs/redeploy/variable_names,
  tailscale_status, vps_units, db_health
- `quality` (8 +1 helper): gates_run, greptile_review, receipt_approve,
  waiver_record, contract_ack/status, supply_chain_check, secret_scan
- `packs` (9): app_tools_load, api_smoke, supabase_query, push_test,
  feature_flags, crash_reports, scoreboard_get, store_listing_get,
  render_job_status

## Skills (13 + platform/security groups)

code-review, contract-first-changes, debugging, desk-bootstrap, desk-doctor,
desk-gateway, gotxcot-uplift, greptile-merge-gate, hindsight-memory,
ragflow-docs, tool-packs, trackplan-dispatch, verification-receipts;
platforms/{android, deno-typescript, ios, python, railway-tailscale,
remote-dev-machine, rust, terraform-k8s, vercel};
security/{secrets-handling, supply-chain}.

## Contracts / prompts / CI

- Rosters: `_core.yaml` + lead/systems/web/android/ios/infra/quality `.yaml`.
- Tool-packs: clippyos/desklanes/kanbanos `.yaml`; events `desk-live-v1.md`;
  changes `desk-v2-tool-rosters-v1.yaml`.
- Prompts: 7 seat XML + 7 alias XML + `_shared/`; templates `LEAD|SYSTEMS|WEB|
  ANDROID|IOS|INFRA|QUALITY.md` + `spectrumwebco.json` roster.
- CI gates: check_receipt/contracts/desk_integrity/ownership/rollback/secrets
  + run_all; gateway `tests/` (224K).

## Omes landing zones

- `omes/tools/<pack>.py` + `*_TOOL_NAMES` + `register_*` (pack tools).
- `omes/skills/<pack>/SKILL.md` (+ platform/security subskills).
- `omes/routines/<flow>.py|md` (intake/dispatch/consolidate, review flows).
- `omes/contracts/tool-rosters/omes.yaml` + `policies/omes.json` (extend).
- `omes/evals/cases/<pack>.json` (pack behaviour + refusal cases).
- `omes/credentials/` providers per upstream; `pyproject.toml` deps.
