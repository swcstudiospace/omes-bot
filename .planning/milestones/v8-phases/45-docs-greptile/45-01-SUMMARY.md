# Summary 45-01: Docs set, Greptile config, KB pipeline, CI freshness

## What was built

- `omes/tooling/catalog.py`: renders `docs/tool-catalog.md` (109 tools,
  family/description/params/approval) from the live registry; `--check`
  fails on drift. Registry gained `approval_required()`.
- `docs/architecture.md`, `docs/faq.md`, `docs/greptile.md` + SUMMARY
  entries; catalog listed under Build.
- `.greptile/config.json`: strictness 2, logic/syntax/style, status check,
  ignore patterns, instructions, five scoped rules from repo conventions.
- `omes/greptile/kb_sync.py`: MCP streamable-HTTP client (JSON + SSE,
  session echo, paginated) mirroring KB docs into `kb/` with manifest +
  untrusted stamps; exits 2/3/0 on no-key/unenrolled/empty. `kb/README.md`
  committed; generated docs arrive via workflow.
- CI: `docs` job (link tests + catalog `--check`); `kb-refresh.yml`
  (weekly + dispatch, secret-gated, opens update PRs).
- `greptile init` attempted per approval: blocked — the `swcstudiospace`
  org is not on the Greptile workspace (needs org-admin app install).
  Recorded in `docs/greptile.md`; GRE-01 scope adjusted accordingly.

## Verification

`.venv/bin/python -m pytest omes/tests -q` → exit 0, 310 passed
(301 carried + 9 new). No network in tests. No new dependencies.
Workflows parse as YAML; existing CI commands intact.
