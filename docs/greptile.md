# Greptile

Greptile reviews every pull request against this repo's own standards, and
publishes a knowledge base of the codebase back into the docs.

## Connection

The repo side is ready (`.greptile/config.json` below), but connection
itself lives in the Greptile workspace, not in git. Two steps, both outside
this repo:

1. Install the Greptile GitHub App on the `swcstudiospace` organization
   (dashboard, or `greptile settings` → Repositories). This needs an org
   admin — a CLI in this checkout cannot do it.
2. Run `greptile init` in this checkout (or enable the repo in the
   dashboard). New PRs get reviewed automatically from there.

`greptile init` was attempted during v8 and stopped at step 1 with
"not connected to your Greptile workspace" — expected until the app is
installed. If reviews ever stop appearing later, check the dashboard
connection first.

## Review standards

`.greptile/config.json` carries the repo's review posture:

- Logic/syntax/style comments at default strictness, re-run on PR updates,
  with a GitHub status check.
- Generated and scratch paths ignored (planning notes, venvs, caches).
- Structured rules mirroring CONTRIBUTING.md: roster-exactness for new
  tools, hermetic tests, no secrets, receipt-backed claims, linked docs.

Rules use stable ids and repo-root scopes; `omega_prime/tests/test_greptile_config.py`
keeps the file inside the documented schema.

## Knowledge base

Greptile synthesizes a versioned Markdown knowledge base per enrolled repo
(`index.md`, `docs/**`, optional `reverts/**`) and refreshes it on a
schedule. The mirror lives in [`kb/`](../kb/README.md) — outside the
GitBook set on purpose, with each file stamped synthesized/untrusted plus
its section version.

Sync it by hand (needs `GREPTILE_API_KEY` from the org's API settings):

```bash
GREPTILE_API_KEY=... .venv/bin/python -m omega_prime.greptile.kb_sync \
  --repo swcstudiospace/omega-prime --out kb
```

Without a key, an unenrolled repo, or nothing published yet, the sync
exits cleanly and writes nothing — all three are normal states, not errors.
The `kb-refresh` workflow runs the same sync weekly and opens a PR when
the mirror changes.

Enrollment note: KB synthesis is a per-organization rollout, not a default.
If the sync reports the repo unenrolled, ask the Greptile contact to enable
it — no repo change can substitute.
