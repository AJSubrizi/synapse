#!/usr/bin/env bash
# Capture a plain-text demo transcript when vhs/asciinema are unavailable.
# Writes docs/assets/synapse-demo.txt (CI-friendly, no GUI deps).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/docs/assets"
OUT="$ROOT/docs/assets/synapse-demo.txt"
{
  echo "# Synapse demo transcript — $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "# Prefer: brew install vhs && ./scripts/record-demo.sh"
  echo
  bash "$ROOT/scripts/demo.sh" 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
} > "$OUT"
echo "wrote $OUT"
