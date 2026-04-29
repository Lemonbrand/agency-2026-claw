#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${CODEX_MODEL:-gpt-5.2}"
OUT="$(mktemp)"
LOG="$(mktemp)"
trap 'rm -f "$OUT" "$LOG"' EXIT

if ! codex exec \
  -C "$ROOT" \
  --sandbox read-only \
  --model "$MODEL" \
  -c model_reasoning_effort='"high"' \
  --output-last-message "$OUT" \
  - >"$LOG" 2>&1; then
  cat "$LOG" >&2
  exit 1
fi

if [[ ! -s "$OUT" ]]; then
  cat "$LOG" >&2
  echo "codex-brain.sh produced no final message. Check CODEX_MODEL and Codex CLI version." >&2
  exit 1
fi

cat "$OUT"
