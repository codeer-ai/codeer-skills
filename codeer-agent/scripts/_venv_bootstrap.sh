#!/usr/bin/env bash
# Shared Python environment bootstrap for Codeer skill helpers.
set -euo pipefail

SELF="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HERE="$(cd "$(dirname "$SELF")" && pwd)"

CACHE_ROOT="${TMPDIR:-/tmp}/codeer-skills"
VENV="${CODEER_AGENT_VENV:-$CACHE_ROOT/codeer-agent-venv}"
PYTHON_BIN="$VENV/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi

if ! "$PYTHON_BIN" -c "import httpx" >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --disable-pip-version-check --no-cache-dir 'httpx>=0.27' >/dev/null
fi

export PYTHONPATH="$HERE:${PYTHONPATH:-}"
export CODEER_AGENT_PYTHON="$PYTHON_BIN"
