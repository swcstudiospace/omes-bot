# Summary 28-01: Web tools, skills, and browser vision transport

## What shipped

`omes/tools/webpack.py` (named to avoid the existing `web.py` search module,
which was briefly overwritten and restored byte-identical): 6 registry tools
porting desk `web.py` (Vercel lifecycle behind a project allowlist, preview
checks via an injectable fetcher, bundle secret scans) plus `web_review_page`
(connectivity + rendered screenshot + vision analysis, vision errors
reported not fatal). Approval on promote/rollback.

`omes/tools/playwright_browser.py`: headless-Chromium transport with an
injectable launcher (no browser binary in tests; `playwright install
chromium` documented for real use). `pyproject.toml` gains
`playwright>=1.40`.

`omes/skills/deno-typescript/SKILL.md`, `omes/skills/vercel/SKILL.md`:
desk skills with `bots:` repointed. Roster, policy, composition extended.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_web.py -q` → exit 0, 6 passed.
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 193 passed (187 + 6).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.
