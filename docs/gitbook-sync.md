# GitBook sync

These docs publish to GitBook straight from this repo via Git
Sync. Content lives in `docs/`; the site config is
`.gitbook.yaml` at the repo root (`root: ./docs/`,
`structure.readme: README.md`, `structure.summary: SUMMARY.md`).

## Connect once (dashboard)

1. In GitBook, create (or open) the Omes Bot space.
2. Top right: **Set up Git Sync**.
3. Authorize the GitHub integration for the `swcstudiospace`
   organization.
4. Map repository `swcstudiospace/omes-bot`, branch `main`,
   directory `/` (the `.gitbook.yaml` points at `docs/`).
5. Publish the space. Later pushes to `main` sync automatically;
   pull requests get preview builds.

## Edit in the repo

With Git Sync on, manage pages in the repository — editing synced
pages in GitBook can create conflicts. Keep `docs/SUMMARY.md`
(to headings + nested links, each file exactly once) matching the
files on disk; `omes/tests/test_docs.py` enforces that.
