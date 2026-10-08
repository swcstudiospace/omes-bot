---
phase: 46-land-hardening
plan: "01"
subsystem: security
tags: [redaction, approvals, leases]
requirements-completed: [LAND-01, LAND-02]
completed: 2026-10-07
status: complete
---

# Summary 46-01: Verify and land the in-flight hardening

**Landed the in-flight tool hardening and reconciled the generated catalog.**

## What was built

- Landed 24 pre-v9 uncommitted files + regenerated `docs/tool-catalog.md`
  (25 files, commit `f508070`): recursive redaction, intake leases, atomic
  store writes, Railway/Play/App-Store binding fixes, receipt/YAML-ack/
  secret-scan hardening, SQL + SSRF guards, screenshot confinement,
  `ult_session_mark` approval, stale-plan refusal, skill headers, env names.
- Fixed the one gate failure found: catalog drift from the approval change
  (regenerated via `omes.tooling.catalog --out`).

## Verification

`HOME=/tmp/fakehome .venv/bin/python -m pytest omes/tests -q` → exit 0,
310 passed (305 carried + 5 new). HOME redirect is a sandbox workaround for
the PyRIT home-dir write; the real fix is DPT-01 (Phase 51).
`omes.evals.runner` → exit 0, 23 passed. `assemble-prompts.sh --check` →
exit 0. `omes.setup_check` → exit 0. `git status` clean under `omes/`,
`docs/` (only `.planning/` v9 setup edits remain, uncommitted per
`commit_docs=false`).

## Follow-ups

- `_safe_shot_name` duplicated in `mobile.py` + `webpack.py` — dedupe
  if a shared helper module appears.
- Test-suite HOME isolation becomes DPT-01; discord 3.13+ guard is HYG-05.
