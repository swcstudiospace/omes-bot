# Conventions: desk rules to keep, Omega Prime rules to hold

## Desk conventions (port the behaviour, not the scaffolding)

- Verification receipts: completion claims cite commands + exit codes
  (Omega Prime PD-1 already; desk `check_receipt.py` is the stricter reference).
- Fail-open reads, fail-closed writes: reads return data + error payloads,
  never raise; writes need approval (`approval_id` → Omega Prime `ApprovalLog`).
- Rosters are versioned contracts: `name/kind/gates/backend/input`; tool
  packs declare the 20-tool ceiling per ticket (`tool-packs` skill).
- Ownership: last match wins, unowned fails (`ownership_resolve`).
- Contract-first changes: breaking-change analysis + versioning + consumer
  ack (`contract_propose/ack`, `changes/*.yaml`).
- Secrets never in transcripts; per-project allowlists on upstreams.
- No seat approves its own receipt (lead/quality separation → Omega Prime: approval
  must come from a person, never the bot id — already the rule).

## Omega Prime conventions (do not break)

- One Python process, one agent; stdlib-first core, pip deps only for
  third-party integrations (v4 precedent).
- Registry tools return JSON-safe dicts; `*_TOOL_NAMES` + drift guard;
  roster lists exactly the registered names (tests enforce).
- Fake transports/peers in tests; no live credentials, no network in suite.
- A phase is done when its parity checks pass; claims cite command + exit code.
