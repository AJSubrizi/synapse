#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local/bin}"
BRAIN_HOME="${BRAIN_HOME:-$HOME/AI-Brain}"
case "${SHELL:-}" in
  *bash) DEFAULT_RC="$HOME/.bashrc" ;;
  *)     DEFAULT_RC="$HOME/.zshrc" ;;
esac
SHELL_RC="${SHELL_RC:-$DEFAULT_RC}"
DELETE_VAULT=0

if [ "${1:-}" = "--delete-vault" ]; then
  DELETE_VAULT=1
fi

# Restore any real binaries that the agent wrappers replaced, then remove the
# wrappers. Skipping this would leave commands like `codex` pointing at a deleted
# brain shim (broken until manually fixed).
REAL_DIR="$PREFIX/.brain-real"
if [ -d "$REAL_DIR" ]; then
  for real in "$REAL_DIR"/*; do
    [ -e "$real" ] || [ -L "$real" ] || continue
    name="$(basename "$real")"
    if [ -e "$PREFIX/$name" ] && grep -q "$PREFIX/brain" "$PREFIX/$name" 2>/dev/null; then
      rm -f "$PREFIX/$name"
    fi
    mv "$real" "$PREFIX/$name"
    echo "Restored $name -> $PREFIX/$name"
  done
  rmdir "$REAL_DIR" 2>/dev/null || true
fi

rm -f "$PREFIX/brain"
echo "Removed $PREFIX/brain"

if [ -f "$SHELL_RC" ] && grep -q "Agent Brain Runtime" "$SHELL_RC"; then
  cp "$SHELL_RC" "$SHELL_RC.brain-bak"
  awk '
    /# >>> Agent Brain Runtime >>>/ { skip=1 }
    skip && /# <<< Agent Brain Runtime <<</ { skip=0; next }
    !skip { print }
  ' "$SHELL_RC.brain-bak" > "$SHELL_RC"
  echo "Removed Agent Brain Runtime block from $SHELL_RC (backup: $SHELL_RC.brain-bak)"
else
  echo "No Agent Brain Runtime block found in $SHELL_RC"
fi

if [ "$DELETE_VAULT" = "1" ]; then
  rm -rf "$BRAIN_HOME"
  echo "Deleted $BRAIN_HOME"
else
  echo "Kept vault at $BRAIN_HOME"
fi

