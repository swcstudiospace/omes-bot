---
milestone: v8
audited: 2026-10-03T20:30:00Z
status: passed
scores:
  requirements: 7/7
  phases: 2/2
  integration: 5/5
  flows: 2/2
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - Prose counts (tests/evals) refresh by hand at milestone close; no generator yet
  - Greptile workspace connection pending (org app install, user dashboard step)
  - KB synthesis enrollment pending (per-org rollout; needs Greptile contact + org API key)
  - CODEOWNERS/FUNDING.yml skipped (no confirmed handle/team/sponsor to name)
---

# Milestone v8 Audit: Public launch

## Requirements (7/7)

| Requirement | Phase | Verified by |
|-------------|-------|-------------|
| PUB-01..03 | 44 | 44-VERIFICATION.md |
| DOC-04, GRE-01, GRE-02, CIC-01 | 45 | 45-VERIFICATION.md |

Adjustment (recorded, not hidden): GRE-01 originally required the repo
connected via `greptile init`. The approved `init` run stopped at the
org-level gate (`swcstudiospace` not on the Greptile workspace — needs an
org-admin app install). Scope adjusted to repo-side config + guide +
recorded attempt; the dashboard step is the user's. No orphans otherwise.

## Phases (2/2)

All phases `complete`, all canonical verifications `passed`.

## Integration (5/5)

- Suite: 310 pytest passed (294 carried + 16 new).
- Deterministic evals: 23/23 passed (CI assertion extended for the docs job).
- Prompt assembly + setup check: exit 0; template sections stay empty.
- Workflows parse as YAML; existing three CI commands byte-intact; catalog
  `--check` green on the committed page.
- No new dependencies; no network in tests; docs set passes SUMMARY/link rules.

## Flows (2/2)

- Docs freshness: editing any tool description breaks `catalog --check`
  until regen (proven by the drift test); README/SUMMARY links resolve by test.
- KB sync: scripted MCP peers (JSON + SSE, paginated) round-trip to a
  stamped mirror + manifest; no-key/unenrolled/empty skips verified.
  Live fetch blocked on key + enrollment (expected, documented).

## Deferred (accepted)

- GitHub Pages deploy (user chose GitBook-only).
- Per-module API reference (catalog covers the surface).
- Live KB content + review activation (user dashboard steps).
- Merging the PR (user reviews and merges).
