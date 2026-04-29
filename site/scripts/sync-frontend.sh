#!/bin/bash
# Frontend-side sync: copy existing branded dashboards into public/embeds and
# seed env.json. Codex's public-export handles public/data/. This script handles
# the parts the frontend owns.
#
# Idempotent. Safe to run repeatedly.

set -euo pipefail

SITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$SITE/.." && pwd)"
WEB="$ROOT/web"
EMBEDS="$SITE/public/embeds"
DATA="$SITE/public/data"
CHARTS="$DATA/charts"

mkdir -p "$EMBEDS" "$DATA" "$CHARTS"

# 1. Copy the existing branded dashboards into embeds for iframe sources.
for f in dashboard.html sovereignty.html agency-loop-audit.html; do
  if [ -f "$WEB/$f" ]; then
    cp "$WEB/$f" "$EMBEDS/$f"
    echo "embed: $f"
  else
    echo "warn: $WEB/$f missing (iframe will 404 until backend produces it)"
  fi
done

# 2. Stub data/* if Codex's public-export has not yet produced them, so the
# frontend renders 'data loading' chips rather than fetch errors.
for f in app-manifest.json overview.json challenges.json findings-index.json audit-summary.json execution-proof.json qa-context.json; do
  if [ ! -f "$DATA/$f" ]; then
    case "$f" in
      challenges.json|findings-index.json|execution-proof.json) printf '[]' > "$DATA/$f" ;;
      *) printf '{}' > "$DATA/$f" ;;
    esac
    echo "stub: data/$f"
  fi
done
for f in hhi-by-department.json tri-jurisdictional-sankey.json cost-over-time.json; do
  if [ ! -f "$CHARTS/$f" ]; then
    printf '{}' > "$CHARTS/$f"
    echo "stub: charts/$f"
  fi
done

# 3. env.json — disposable event OpenRouter key, set by Simon out-of-band.
# Never overwrite if it already exists.
if [ ! -f "$SITE/public/env.json" ]; then
  cat > "$SITE/public/env.json" <<'EOF'
{
  "openrouter_key": "",
  "freeze_at_utc": "2026-04-29T18:00:00Z",
  "note": "Replace openrouter_key with the disposable event key. Capped at $50, rotated post-event."
}
EOF
  echo "stub: env.json (replace openrouter_key with the disposable event key)"
fi

echo "sync-frontend: done"
