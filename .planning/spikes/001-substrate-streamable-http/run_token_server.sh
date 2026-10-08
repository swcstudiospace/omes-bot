#!/usr/bin/env bash
# Spike 001, optional auth leg: a throwaway second substrate-mcp in token mode.
#
# The long-running substrate on 127.0.0.1:7410 is anonymous (no SUBSTRATE_TOKEN_*
# configured), so it cannot show the 401 path. This starts the same, unmodified
# agent-substrate server on 127.0.0.1:${PORT:-17411} with a scrubbed environment:
#   - env -i: no inherited store URLs, API keys or real tokens
#   - bun --no-env-file: bun does not auto-load any .env from the agent-substrate tree
#   - one dummy, non-secret token mapped to surface grok-bot
#   - no SUBSTRATE_PG_URL / GREPTIME_URL: no stores, nothing is written anywhere
# It runs in the foreground; stop it with Ctrl-C / SIGTERM (the server exits on both).
set -euo pipefail

PORT="${PORT:-17411}"
SUBSTRATE_REPO="${SUBSTRATE_REPO:-/root/src/repos/agent-substrate}"
BUN="$(command -v bun)"
DUMMY_TOKEN="spike001-dummy-token-not-a-secret"

if (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null; then
	echo "port ${PORT} is already in use; set PORT=<free port>" >&2
	exit 1
fi

cd "${SUBSTRATE_REPO}"
exec env -i \
	PATH="${PATH}" \
	HOME="${HOME}" \
	SUBSTRATE_HOST=127.0.0.1 \
	SUBSTRATE_PORT="${PORT}" \
	SUBSTRATE_TOKEN_GROK_BOT="${DUMMY_TOKEN}" \
	"${BUN}" --no-env-file packages/mcp-server/src/index.ts
