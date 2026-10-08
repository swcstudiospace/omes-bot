# Summary 28-01: Web tools, skills, and browser vision transport

## What shipped

`omega_prime/tools/webpack.py` (named to avoid the existing `web.py` search module,
which was briefly overwritten and restored byte-identical): 6 registry tools
porting desk `web.py` (Vercel lifecycle behind a project allowlist, preview
checks via an injectable fetcher, bundle secret scans) plus `web_review_page`
(connectivity + rendered screenshot + vision analysis, vision errors
reported not fatal). Approval on promote/rollback.

`omega_prime/tools/playwright_browser.py`: headless-Chromium transport with an
injectable launcher (no browser binary in tests; `playwright install
chromium` documented for real use). `pyproject.toml` gains
`playwright>=1.40`.

`omega_prime/skills/deno-typescript/SKILL.md`, `omega_prime/skills/vercel/SKILL.md`:
desk skills with `bots:` repointed. Roster, policy, composition extended.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_web.py -q` → exit 0, 6 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 193 passed (187 + 6).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
