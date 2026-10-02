#!/usr/bin/env bash
# Prepend prompts/_shared/core-directives.xml to prompts/bot-00-omes.xml and
# write prompts-assembled/OMES.xml.
# Substitutes {{DEFAULT_BRANCH}}, {{BOT_ID}}, and {{ROSTER_VERSION}} from
# grokbot/rosters/default.json. A leftover {{...}} is an error.
# A skill or routine named in grokbot/templates/OMES.md must exist on disk.
#
#   scripts/assemble-prompts.sh [--roster <path>] [--check]
#
#   --roster <path>  Roster JSON (default: grokbot/rosters/default.json).
#   --check          Compare against prompts-assembled/OMES.xml. Writes nothing.
set -euo pipefail

OMES="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$OMES/.." && pwd)"
export PYTHONPATH="${REPO}${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m omes.assemble --root "$OMES" "$@"
