#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Turnkey 1-Click Launcher for Grok Bot Native Omega Prime Integration.

set -euo pipefail

# Locate repository root robustly
CURRENT_DIR="$(pwd)"
REPO_ROOT="$CURRENT_DIR"
while [ "$REPO_ROOT" != "/" ] && [ ! -f "$REPO_ROOT/pyproject.toml" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    # Fallback based on script location
    SOURCE="${BASH_SOURCE[0]}"
    while [ -h "$SOURCE" ]; do
        DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
    done
    REPO_ROOT="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    while [ "$REPO_ROOT" != "/" ] && [ ! -f "$REPO_ROOT/pyproject.toml" ]; do
        REPO_ROOT="$(dirname "$REPO_ROOT")"
    done
fi

if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
else
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_ROOT"

exec "$PYTHON_BIN" -m omega_prime.grokbot.oneclick "$@"
