#!/bin/bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

for loop in [0-9][0-9]-*; do
  [ -d "$loop" ] || continue
  session="agency-correct-$loop"
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "skip $session"
    continue
  fi
  cp correction-run.sh "$loop/correction-run.sh"
  chmod +x "$loop/correction-run.sh"
  tmux new-session -d -s "$session" "cd $ROOT/$loop && ./correction-run.sh; bash"
  echo "start $session"
done
