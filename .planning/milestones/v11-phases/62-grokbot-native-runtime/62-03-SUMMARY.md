---
phase: 62-grokbot-native-runtime
plan: "03"
subsystem: grokbot-manifest
tags: [manifest, drift, template-lint, digest]
requires:
  - phase: 62
    provides: `load_runtime` (served and approval-gated tool names) from 62-01
provides:
  - Manifest that lists exactly the tools the host serves, plus approval-gated tools
  - Config-derived capabilities, endpoints, content digest and `bot.integrity`
  - Drift sync that compares only content Grok Bot would see
affects: [62-06, 63-08, 63-06]
tech-stack:
  added: []
  patterns: [single runtime build per manifest, semantic-section diff]
key-files:
  modified:
    - omega_prime/grokbot/manifest.py
    - omega_prime/grokbot/sync.py
    - omega_prime/tests/test_grokbot_manifest.py
    - omega_prime/tests/test_grokbot_sync.py
  created:
    - omega_prime/tests/test_grokbot_lint.py
key-decisions:
  - "The token value never appears in a manifest; `auth_token` only decides `auth.type`."
  - "A wildcard bind (`0.0.0.0`, `::`) is rewritten to `127.0.0.1` with `url_note`; `public_url` wins."
  - "Sync compares instructions, skills, routines, tools, approval_required and capabilities, and ignores url/command/transport/auth/endpoints/digest."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 62-03 Truthful manifest, template lint, drift sync

Commit `b6392ad` (rebased: `9e4d0c3`). Requirements: GRK-06, GRK-09.

## What shipped

Before: `tools` was the static 146-name roster while the host served 108, `capabilities` were hard-coded
`True` (including `prime_agent` with every Prime family off), the version was hard-coded, and `sync --check`
reported false drift for any non-default URL. Now `mcp_server.tools` equals `load_runtime(...).tool_names`
(108), `approval_required` lists the 36 gated tools, `prime_agent` is true only when a Prime family is on,
and `lint_template` proves every skill and routine named by the template exists on disk.

## Verified

`sync --check` of a manifest exported with `--transport stdio` against the live default reports IN SYNC
(exit 0); flipping a Prime flag is reported as drift in the right sections.

## Known limitation

`default_registry` and `load_config` read Prime-family flags from `os.environ`, not from an injected `env`,
so `generate_manifest(env=...)` can change `capabilities` without changing the served tools. Production
passes `os.environ`, so the two agree; an `env` override that also flips the served tools needs
`default_registry` to read flags from `env`.
