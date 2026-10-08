#!/usr/bin/env bash
# Prepend prompts/_shared/core-directives.xml to prompts/bot-00-omega-prime.xml and
# write prompts-assembled/OMEGA_PRIME.xml.
# Substitutes {{DEFAULT_BRANCH}}, {{BOT_ID}}, and {{ROSTER_VERSION}} from
# grokbot/rosters/default.json. A leftover {{...}} is an error.
# A skill or routine named in grokbot/templates/OMEGA_PRIME.md must exist on disk.
#
#   scripts/assemble-prompts.sh [--roster <path>] [--check]
#
#   --roster <path>  Roster JSON (default: grokbot/rosters/default.json).
#   --check          Compare against prompts-assembled/OMEGA_PRIME.xml. Writes nothing.
set -euo pipefail

OMEGA_PRIME="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$OMEGA_PRIME/.." && pwd)"
export PYTHONPATH="${REPO}${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m omega_prime.assemble --root "$OMEGA_PRIME" "$@"
