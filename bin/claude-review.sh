#!/usr/bin/env bash
set -euo pipefail

MODEL="${CLAUDE_MODEL:-sonnet}"
EFFORT="${CLAUDE_EFFORT:-low}"

claude -p \
  --model "$MODEL" \
  --effort "$EFFORT" \
  --permission-mode dontAsk \
  --output-format text \
  --no-session-persistence \
  --disable-slash-commands \
  "$(cat)"
