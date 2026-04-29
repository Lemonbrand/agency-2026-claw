#!/bin/bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

printf "%-32s %-10s %-8s %-10s %s\n" "loop" "tmux" "rc" "brief_KB" "last_event"
printf "%-32s %-10s %-8s %-10s %s\n" "----" "----" "--" "--------" "----------"
for loop in [0-9][0-9]-*; do
  [ -d "$loop" ] || continue
  session="agency-correct-$loop"
  if tmux has-session -t "$session" 2>/dev/null; then tmux_state="running"; else tmux_state="stopped"; fi
  rc="-"
  if [ -f "$loop/correction.log" ]; then
    rc="$(grep -o 'correction end rc=[0-9]*' "$loop/correction.log" | tail -1 | sed 's/.*=//')"
  fi
  kb="0"
  [ -f "$loop/research-brief.md" ] && kb="$(du -k "$loop/research-brief.md" | awk '{print $1}')"
  last=""
  [ -f "$loop/correction.log" ] && last="$(grep '=== correction' "$loop/correction.log" | tail -1)"
  printf "%-32s %-10s %-8s %-10s %s\n" "$loop" "$tmux_state" "$rc" "$kb" "$last"
done
