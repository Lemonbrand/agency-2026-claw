#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

NEOTOMA_BIN="$ROOT/.runtime/neotoma/node_modules/.bin/neotoma"
if [ ! -x "$NEOTOMA_BIN" ]; then
  echo "Project-local Neotoma is missing. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

export NEOTOMA_DATA_DIR="${NEOTOMA_DATA_DIR:-$ROOT/.neotoma/data}"
export NEOTOMA_HTTP_PORT="${NEOTOMA_PORT:-3187}"
export NEOTOMA_ENV="${NEOTOMA_ENV:-production}"

# Simon's global shell exports NEOTOMA_API_ONLY for the VPS tunnel. This repo
# needs offline/local transport unless a command explicitly asks for API mode.
unset NEOTOMA_API_ONLY

exec "$NEOTOMA_BIN" "$@"
