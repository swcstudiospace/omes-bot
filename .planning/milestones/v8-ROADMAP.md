# Roadmap: Omega Prime

## Milestones

- ✅ **v1 One Omega Prime agent** — Phases 1-12 (shipped 2026-10-03)
- ✅ **v2 Enterprise hardening** — Phases 13-16 (shipped 2026-10-03)
- ✅ **v3 Grok Bot** — Phases 17-20 (shipped 2026-10-03)
- ✅ **v4 Third-party integrations** — Phases 21-25 (shipped 2026-10-03)
- ✅ **v5 Desk packs** — Phases 26-33 (shipped 2026-10-03)
- ✅ **v6 Grok ship** — Phases 34-38 (shipped 2026-10-03)
- ✅ **v7 Substrate surface** — Phases 39-43 (shipped 2026-10-03)
- 🚧 **v8 Public launch** — Phases 44-45 (in progress)

Archives: `milestones/v1-ROADMAP.md` through `milestones/v7-ROADMAP.md`
with phase directories under `milestones/v1-phases/` through
`milestones/v7-phases/`.

## v8 Overview

v7 plugged Omega Prime into the substrate (see `milestones/v7-ROADMAP.md`). v8
launches the repo in public: a README with real branding, the standard
public-repo files, richer GitBook docs with a generated tool catalog kept
fresh by CI, Greptile connected with repo review standards, and a KB sync
pipeline that publishes Greptile's knowledge base into the docs on a
schedule. Numbering continues. A phase is done when its success criteria
pass; the milestone ships with a pushed branch + PR.

## Phases

- [x] **Phase 44: Public files + branding** - README, standards files, art. (completed 2026-10-03)
- [x] **Phase 45: Docs + Greptile + CI** - Rich docs, KB pipeline, freshness. (completed 2026-10-03)

## Phase Details

### Phase 44: Public files + branding

**Goal**: The repo looks and reads like a public launch.
**Depends on**: v7 complete
**Requirements**: PUB-01, PUB-02, PUB-03
**Success Criteria** (what must be TRUE):

  1. README carries the icon/banner, badges, tour, quickstart, and links, with every link resolving.
  2. All standard files exist with project-true content (no placeholder names/emails), and packaging metadata is public-complete.
  3. Icon + banner SVGs render (valid SVG) and are referenced from README and docs.

Plans:

- [x] 44-01: Brand, README, standard files

### Phase 45: Docs + Greptile + CI

**Goal**: Docs stay rich and fresh; Greptile reviews and publishes.
**Depends on**: Phase 44
**Requirements**: DOC-04, GRE-01, GRE-02, CIC-01
**Success Criteria** (what must be TRUE):

  1. New docs pages pass the SUMMARY/link rules and read true against the code.
  2. `.greptile/` config validates against the documented keys; the guide covers connect → review → KB; the `init` attempt and its org-level blocker are recorded.
  3. The KB sync script round-trips a scripted MCP peer and skips cleanly without credentials; the scheduled workflow exists and is secret-safe.
  4. CI verifies links + catalog currency on push/PR with the existing three commands intact.

Plans:

- [x] 45-01: Docs set, Greptile config, KB pipeline, CI freshness
