#!/bin/bash
# Single-loop runner. Aider + GLM 5.1 via OpenRouter, iterating on research-brief.md.
# Cwd is the per-challenge directory. Reads PROMPT.md, ITERATE.md, STRUCTURE.md.

set -u

LOOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$LOOP_DIR/.." && pwd)"
MAX_ITERATIONS="${MAX_ITERATIONS:-12}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-3}"

cd "$LOOP_DIR"

# Load OpenRouter key (must use -a so aider sees the env var)
set -a
# shellcheck disable=SC1091
source /etc/lemonclaw/openrouter.env
set +a

PROGRESS="progress.log"
echo "=== loop start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$PROGRESS"

# Seed research-brief.md if missing
if [ ! -s research-brief.md ]; then
  cat > research-brief.md <<'EOF'
# Research Brief — work in progress

(This file is being authored iteratively by an agentic loop. It will be replaced as the loop runs.)

## 1. Build Approach

## 2. Data Required (and what's missing)

## 3. Potential Sources for Missing Data

## 4. Methodology

## 5. Observability and Provability

## 6. Citation Pack (jury-ready)
EOF
fi

for i in $(seq 1 "$MAX_ITERATIONS"); do
  ITER_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "--- iteration $i / $MAX_ITERATIONS  start=$ITER_START ---" >> "$PROGRESS"

  # Build the per-iteration message: the iteration instruction + read-in references
  aider \
    --model openrouter/z-ai/glm-5.1 \
    --no-pretty --no-stream --yes-always --no-auto-commits \
    --read PROMPT.md \
    --read "$ROOT/STRUCTURE.md" \
    --read "$ROOT/ITERATE.md" \
    --read "$ROOT/KNOWN-DATA-ISSUES-NOTES.md" \
    --read "$ROOT/VERIFIED_SCHEMA.md" \
    --read "$ROOT/CORRECTION_PASS.md" \
    --message "Iterate on research-brief.md per ITERATE.md and CORRECTION_PASS.md. First correct schema/table/column hallucinations using VERIFIED_SCHEMA.md, then improve the weakest section. This is iteration $i of $MAX_ITERATIONS." \
    research-brief.md \
    >> "$PROGRESS" 2>&1 || echo "aider exit $?" >> "$PROGRESS"

  # Check completion signal at the very top of research-brief.md
  if head -1 research-brief.md | grep -q "<status>COMPLETE</status>"; then
    echo "=== COMPLETE at iteration $i  $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$PROGRESS"
    exit 0
  fi

  echo "--- iteration $i done  end=$(date -u +%Y-%m-%dT%H:%M:%SZ) ---" >> "$PROGRESS"
  sleep "$SLEEP_BETWEEN"
done

echo "=== exhausted $MAX_ITERATIONS iterations  $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$PROGRESS"
exit 0
