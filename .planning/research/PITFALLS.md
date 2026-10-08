# Pitfalls Research: v9 SOTA upgrade

**Date:** 2026-10-07
**Mode:** Inline (GSD research agents unavailable in this runtime)

## Pitfalls and prevention

1. **Ruff version drift**: a linter is not semver-stable in what it flags.
   Prevention: pin exactly in a dev extra; CI installs from the extra.
2. **Checker churn on 172 files**: first typecheck run yields hundreds of errors.
   Prevention: land in one hygiene phase, fix to zero, enforce after.
3. **audioop removal (3.13+)**: `import discord` fails on 3.13/3.14.
   Prevention: guard the import before adding new Pythons to the matrix.
4. **PyRIT home-dir writes**: DuckDB/memory writes under `~/.local/share`
   break hermetic runs and sandboxes. Prevention: per-test HOME/data isolation.
5. **Streaming breaking FakeTransport**: new Transport methods must exist on
   the fake or every provider test breaks. Prevention: extend fake first.
6. **Responses echo burden**: Responses callers must echo reasoning items per
   turn; restricted keys may lack `api.responses.write`. Prevention: default
   Responses only for api.openai.com, fallback to chat_completions on 401/403.
7. **Dirty-tree conflicts**: 24 uncommitted files predate the milestone.
   Prevention: land + verify them as Phase 46 before any other change.
8. **Scope creep into live verification**: deferred since v1 for a reason.
   Prevention: hermetic rule stays; live probes remain manual opt-in.
