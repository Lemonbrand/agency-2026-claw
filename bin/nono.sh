#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

NEOTOMA_PORT="${NEOTOMA_PORT:-3187}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8765}"

if ! command -v nono >/dev/null 2>&1; then
  echo "nono is not installed. Run: brew install nono" >&2
  exit 127
fi

if [ "$#" -eq 0 ]; then
  set -- claude
fi

exec nono run \
  --profile claude-code \
  --allow "$ROOT" \
  --read "$HOME/lemon" \
  --allow-port "$NEOTOMA_PORT" \
  --allow-bind "$DASHBOARD_PORT" \
  --no-rollback \
  -- "$@"
