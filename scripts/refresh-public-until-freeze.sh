#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FREEZE_ISO="${FREEZE_ISO:-2026-04-29T18:00:00Z}"
REFRESH_INTERVAL="${REFRESH_INTERVAL:-60}"

FREEZE_EPOCH="$(
  FREEZE_ISO="$FREEZE_ISO" .venv/bin/python - <<'PY'
import datetime
import os

iso = os.environ["FREEZE_ISO"].replace("Z", "+00:00")
print(int(datetime.datetime.fromisoformat(iso).timestamp()))
PY
)"

echo "refresh loop until ${FREEZE_ISO} every ${REFRESH_INTERVAL}s"

while [ "$(date -u +%s)" -lt "$FREEZE_EPOCH" ]; do
  if [ -x sovereignty-tracker/poll_local.py ]; then
    (cd sovereignty-tracker && ./poll_local.py) || true
  fi
  if [ -x sovereignty-tracker/tracker.py ]; then
    (cd sovereignty-tracker && ./tracker.py) || true
  fi
  ./bin/agency public-export
  sleep "$REFRESH_INTERVAL"
done

./bin/agency public-export
echo "refresh loop frozen at ${FREEZE_ISO}"
