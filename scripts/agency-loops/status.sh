#!/bin/bash
# Snapshot status of all 10 agency loops. Run on the VPS.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOOPS=$(ls -d [0-9]*/  | sed 's|/$||' | sort)

printf '%-32s  %-10s  %-6s  %-7s  %-9s  %s\n' "loop" "tmux" "iter" "status" "brief_KB" "last_event"
printf '%-32s  %-10s  %-6s  %-7s  %-9s  %s\n' "----" "----" "----" "------" "--------" "----------"

for loop in $LOOPS; do
  session="agency-$loop"
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux_state="running"
  else
    tmux_state="stopped"
  fi

  iter=$(grep -c "^--- iteration" "$loop/progress.log" 2>/dev/null || echo 0)
  if grep -q "<status>COMPLETE</status>" "$loop/research-brief.md" 2>/dev/null; then
    state="DONE"
  elif grep -q "=== exhausted" "$loop/progress.log" 2>/dev/null; then
    state="EXHAUSTED"
  elif [ "$tmux_state" = "running" ]; then
    state="active"
  else
    state="idle"
  fi

  if [ -f "$loop/research-brief.md" ]; then
    kb=$(awk 'END {printf "%.1f", NR/8}' "$loop/research-brief.md" 2>/dev/null || echo 0)
    bytes=$(wc -c < "$loop/research-brief.md")
    kb=$(awk -v b=$bytes 'BEGIN {printf "%.1f", b/1024}')
  else
    kb="-"
  fi

  last=$(tail -1 "$loop/progress.log" 2>/dev/null | cut -c1-60)

  printf '%-32s  %-10s  %-6s  %-9s  %-8s  %s\n' "$loop" "$tmux_state" "$iter" "$state" "$kb" "$last"
done
