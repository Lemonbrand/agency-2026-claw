#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/neotoma.sh" --offline store \
  --user-id "${AGENCY_TENANT_ID:-agency-2026-local}" \
  --idempotency-key "agency-2026-smoke" \
  --entities '[{"entity_type":"investigation","name":"local-neotoma-smoke","status":"candidate","source":"smoke-neotoma.sh"}]'
