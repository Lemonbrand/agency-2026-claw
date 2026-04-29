#!/bin/bash
set -u

LOOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$LOOP_DIR/.." && pwd)"
cd "$LOOP_DIR"

set -a
# shellcheck disable=SC1091
source /etc/lemonclaw/openrouter.env
set +a

TS="$(date -u +%Y%m%dT%H%M%SZ)"
cp research-brief.md "research-brief.md.pre-correction.$TS"
echo "=== correction start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> correction.log

aider \
  --model openrouter/z-ai/glm-5.1 \
  --no-pretty --no-stream --yes-always --no-auto-commits \
  --read PROMPT.md \
  --read "$ROOT/STRUCTURE.md" \
  --read "$ROOT/KNOWN-DATA-ISSUES-NOTES.md" \
  --read "$ROOT/VERIFIED_SCHEMA.md" \
  --read "$ROOT/CORRECTION_PASS.md" \
  --message "Run the correction pass now. Edit research-brief.md directly. First add Current executable status and Presentation sentence if missing. Then audit every schema.table.column reference against VERIFIED_SCHEMA.md. Replace invalid references with verified equivalents or mark [GAP]. Remove or correct non-existent views/tables/columns named in CORRECTION_PASS.md. Add one executable SQL sketch using only verified schema, or state exactly why no executable SQL is possible. Keep the six-section structure. Be concise. Do not invent examples, URLs, entity IDs, ref numbers, or citations." \
  research-brief.md \
  >> correction.log 2>&1
RC=$?
echo "=== correction end rc=$RC $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> correction.log
exit "$RC"
