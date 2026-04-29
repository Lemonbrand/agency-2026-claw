#!/bin/bash
# Launch all 10 agency loops in parallel tmux sessions.
# Run on the VPS, cwd /opt/lemon-agency.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOOPS=$(ls -d [0-9]*/  | sed 's|/$||' | sort)

if [ -z "$LOOPS" ]; then
  echo "No loop directories found." >&2
  exit 1
fi

LAUNCHED=0
SKIPPED=0
for loop in $LOOPS; do
  session="agency-$loop"
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "skip  $session (already running)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  cp run-template.sh "$loop/run.sh"
  chmod +x "$loop/run.sh"

  tmux new-session -d -s "$session" "cd $ROOT/$loop && ./run.sh; bash"
  echo "start $session"
  LAUNCHED=$((LAUNCHED+1))
done

echo
echo "launched=$LAUNCHED skipped=$SKIPPED"
echo "monitor: ./status.sh"
echo "attach:  tmux attach -t agency-01-zombie-recipients"
