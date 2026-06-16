#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local/bin}"
BRAIN_HOME="${BRAIN_HOME:-${SYNAPSE_HOME:-$HOME/Synapse}}"
case "${SHELL:-}" in
  *bash) DEFAULT_RC="$HOME/.bashrc" ;;
  *)     DEFAULT_RC="$HOME/.zshrc" ;;
esac
SHELL_RC="${SHELL_RC:-$DEFAULT_RC}"
DELETE_VAULT=0

if [ "${1:-}" = "--delete-vault" ]; then
  DELETE_VAULT=1
fi

REAL_DIR="$PREFIX/.synapse-real"
LEGACY_REAL="$PREFIX/.brain-real"
for dir in "$REAL_DIR" "$LEGACY_REAL"; do
  if [ -d "$dir" ]; then
    for real in "$dir"/*; do
      [ -e "$real" ] || [ -L "$real" ] || continue
      name="$(basename "$real")"
      if [ -e "$PREFIX/$name" ] && grep -qE "$PREFIX/(synapse|brain)" "$PREFIX/$name" 2>/dev/null; then
        rm -f "$PREFIX/$name"
      fi
      mv "$real" "$PREFIX/$name"
      echo "Restored $name -> $PREFIX/$name"
    done
    rmdir "$dir" 2>/dev/null || true
  fi
done

rm -f "$PREFIX/synapse" "$PREFIX/brain"
echo "Removed $PREFIX/synapse and $PREFIX/brain"

if [ -f "$SHELL_RC" ] && grep -qE "Synapse|Agent Brain Runtime" "$SHELL_RC"; then
  cp "$SHELL_RC" "$SHELL_RC.synapse-bak"
  awk '
    /# >>> Synapse >>>/ { skip=1 }
    skip && /# <<< Synapse <<</ { skip=0; next }
    /# >>> Agent Brain Runtime >>>/ { skip=1 }
    skip && /# <<< Agent Brain Runtime <<</ { skip=0; next }
    !skip { print }
  ' "$SHELL_RC.synapse-bak" > "$SHELL_RC"
  echo "Removed Synapse block from $SHELL_RC (backup: $SHELL_RC.synapse-bak)"
else
  echo "No Synapse block found in $SHELL_RC"
fi

if [ "$DELETE_VAULT" = "1" ]; then
  rm -rf "$BRAIN_HOME"
  echo "Deleted $BRAIN_HOME"
else
  echo "Kept vault at $BRAIN_HOME"
fi
