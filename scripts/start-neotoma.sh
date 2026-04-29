#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/neotoma.sh" api start --env prod --background
"$ROOT/scripts/neotoma.sh" api status
