#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 127
fi

uv venv .venv
uv pip install -e .

NEOTOMA_PACKAGE_VERSION="${NEOTOMA_PACKAGE_VERSION:-0.4.3}"
mkdir -p .runtime/neotoma .neotoma/data data/raw data/parquet data/findings state web

if [ ! -x .runtime/neotoma/node_modules/.bin/neotoma ]; then
  npm install --prefix .runtime/neotoma "neotoma@$NEOTOMA_PACKAGE_VERSION"
fi

./scripts/neotoma.sh init \
  --data-dir "$ROOT/.neotoma/data" \
  --skip-env \
  --scope skip \
  --configure-mcp no \
  --configure-cli no >/dev/null

chmod +x bin/agency bin/nono.sh scripts/*.sh scripts/*.py

echo "ready: $ROOT"
echo "next: ./scripts/create-demo-data.py && make demo"
