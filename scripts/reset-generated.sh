#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rm -rf "$ROOT/.neotoma/data"
rm -f "$ROOT/data/agency.duckdb" "$ROOT/data/agency.duckdb.wal"
find "$ROOT/data/parquet" -type f ! -name .gitkeep -delete
find "$ROOT/data/findings" -type f ! -name .gitkeep -delete
find "$ROOT/state" -type f ! -name .gitkeep -delete
rm -f "$ROOT/web/dashboard.html"

echo "generated state reset"
