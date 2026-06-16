#!/usr/bin/env bash
# Claude Code Stop hook — run synapse/brain check only when vault/ changed.
set -euo pipefail

ROOT="${SYNAPSE_HOME:-${BRAIN_ROOT:-$HOME/Synapse}}"
VAULT="${BRAIN_VAULT:-$ROOT/vault}"

export BRAIN_ROOT="$ROOT" BRAIN_VAULT="$VAULT"
export BRAIN_SKILLS_DIR="${BRAIN_SKILLS_DIR:-$VAULT/skills}"

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git -C "$ROOT" diff --quiet -- vault 2>/dev/null &&
     git -C "$ROOT" diff --cached --quiet -- vault 2>/dev/null; then
    exit 0
  fi
fi

if command -v synapse >/dev/null 2>&1; then
  exec synapse check
fi
exec brain check
