#!/usr/bin/env bash
# Record the README demo GIF (or asciinema cast) from scripts/demo.sh.
# Prefers vhs; falls back to asciinema if available.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p docs/assets

if command -v vhs >/dev/null 2>&1; then
  echo "recording with vhs -> docs/assets/synapse-demo.gif"
  vhs docs/demo.tape
  echo "done: docs/assets/synapse-demo.gif"
  exit 0
fi

if command -v asciinema >/dev/null 2>&1; then
  cast="docs/assets/synapse-demo.cast"
  echo "recording with asciinema -> $cast"
  asciinema rec --overwrite -c "bash scripts/demo.sh" "$cast"
  echo "done: $cast  (convert with: agg $cast docs/assets/synapse-demo.gif)"
  exit 0
fi

echo "Neither vhs nor asciinema found." >&2
echo "  brew install vhs     # preferred — reads docs/demo.tape" >&2
echo "  brew install asciinema" >&2
echo "Falling back to a plain demo run:" >&2
bash scripts/demo.sh
exit 0
