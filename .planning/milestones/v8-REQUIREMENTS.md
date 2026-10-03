# Requirements: v8 Public launch

Milestone-scoped. v7 requirements are archived in `milestones/v7-REQUIREMENTS.md`.
Ground truth: the shipped tree (README, docs/, CI), the Greptile docs corpus
(`docs-greptile` skill: `.greptile/` config + KB MCP tools), and the live
Greptile CLI (repo not yet connected; org Spectrum Web Co).
User decisions (2026-10-03): connect the repo now via `greptile init`;
push branch + open PR against main; GitBook stays the docs host with
verify-only CI (no Pages deploy).

## Public repo files + branding

- [x] **PUB-01**: README with icon/banner art, badges, feature tour,
  quickstart, and links to docs, template, and contributing.
- [x] **PUB-02**: Standard public-repo files: CONTRIBUTING, CODE_OF_CONDUCT,
  SECURITY, CHANGELOG, .editorconfig, issue + PR templates, CODEOWNERS,
  and public package metadata (license/urls/readme in pyproject).
- [x] **PUB-03**: Icon + banner SVG assets in-repo, referenced from
  README and the docs front page.

## Rich docs + Greptile + docs CI

- [x] **DOC-04**: Richer docs set: architecture tour, FAQ, and a generated
  tool catalog; every page linked once in SUMMARY.
- [x] **GRE-01**: `.greptile/` repo config (review standards from Omes
  conventions) + `docs/greptile.md` integration guide; workspace
  connection attempted via `greptile init` (blocked on org app install —
  user dashboard step, recorded in the guide).
- [x] **GRE-02**: KB sync pipeline: script pulling Greptile KB documents
  (MCP, `GREPTILE_API_KEY`) into `docs/greptile-kb/` plus a scheduled CI
  workflow opening update PRs; skips cleanly without key or enrollment.
- [x] **CIC-01**: Docs freshness in CI: link check + generated-catalog
  currency verified on every push/PR (existing suite/evals/assemble
  commands untouched).

## Future Requirements (deferred)

- GitHub Pages deploy (user chose GitBook-only for v8).
- Greptile KB synthesis enrollment (per-org rollout; needs Greptile contact).
- API reference per module (tool catalog covers the surface for v8).

## Out of Scope

- Merging the PR (user reviews and merges).
- Connecting other repos to Greptile.
- Live KB content today (repo unenrolled; pipeline ships ready).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PUB-01 | Phase 44 | Done |
| PUB-02 | Phase 44 | Done |
| PUB-03 | Phase 44 | Done |
| DOC-04 | Phase 45 | Done |
| GRE-01 | Phase 45 | Done |
| GRE-02 | Phase 45 | Done |
| CIC-01 | Phase 45 | Done |

**Coverage:** 7/7 Done.
