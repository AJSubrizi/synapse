#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local/bin}"
BRAIN_HOME="${BRAIN_HOME:-$HOME/AI-Brain}"
BRAIN_ROOT="${BRAIN_ROOT:-$BRAIN_HOME}"
BRAIN_VAULT="${BRAIN_VAULT:-$BRAIN_ROOT/vault}"
case "${SHELL:-}" in
  *bash) DEFAULT_RC="$HOME/.bashrc" ;;
  *)     DEFAULT_RC="$HOME/.zshrc" ;;
esac
SHELL_RC="${SHELL_RC:-$DEFAULT_RC}"

mkdir -p "$PREFIX" "$BRAIN_ROOT"

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
}

cp "$REPO_DIR/bin/brain" "$PREFIX/brain"
chmod +x "$PREFIX/brain"

if [ ! -d "$BRAIN_VAULT" ]; then
  mkdir -p "$BRAIN_ROOT"
  cp -R "$REPO_DIR/templates/vault" "$BRAIN_VAULT"
fi

mkdir -p \
  "$BRAIN_VAULT/_meta" \
  "$BRAIN_VAULT/concepts" \
  "$BRAIN_VAULT/references" \
  "$BRAIN_VAULT/synthesis" \
  "$BRAIN_VAULT/skills" \
  "$BRAIN_VAULT/projects" \
  "$BRAIN_VAULT/entities" \
  "$BRAIN_VAULT/journal"

copy_if_missing "$REPO_DIR/templates/vault/AGENTS.md" "$BRAIN_VAULT/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/vault/index.md" "$BRAIN_VAULT/index.md"
copy_if_missing "$REPO_DIR/templates/vault/hot.md" "$BRAIN_VAULT/hot.md"
copy_if_missing "$REPO_DIR/templates/vault/log.md" "$BRAIN_VAULT/log.md"
copy_if_missing "$REPO_DIR/templates/vault/_meta/workflow.md" "$BRAIN_VAULT/_meta/workflow.md"
copy_if_missing "$REPO_DIR/templates/vault/_meta/taxonomy.md" "$BRAIN_VAULT/_meta/taxonomy.md"
copy_if_missing "$REPO_DIR/templates/vault/_meta/validate.py" "$BRAIN_VAULT/_meta/validate.py"
copy_if_missing "$REPO_DIR/templates/vault/_meta/dedup.py" "$BRAIN_VAULT/_meta/dedup.py"
copy_if_missing "$REPO_DIR/templates/vault/concepts/workflow.md" "$BRAIN_VAULT/concepts/workflow.md"
chmod +x "$BRAIN_VAULT/_meta/validate.py" "$BRAIN_VAULT/_meta/dedup.py"

copy_if_missing "$REPO_DIR/templates/AGENTS.md" "$HOME/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/CLAUDE.md" "$HOME/CLAUDE.md"
copy_if_missing "$REPO_DIR/templates/GEMINI.md" "$HOME/GEMINI.md"

if ! grep -q "Agent Brain Runtime" "$SHELL_RC" 2>/dev/null; then
  cat >> "$SHELL_RC" <<EOF

# >>> Agent Brain Runtime >>>
export BRAIN_ROOT="$BRAIN_ROOT"
export BRAIN_VAULT="$BRAIN_VAULT"
export BRAIN_BOOT="\$BRAIN_VAULT/AGENTS.md"
export BRAIN_WORKFLOW="\$BRAIN_VAULT/_meta/workflow.md"
export OBSIDIAN_VAULT_PATH="\${OBSIDIAN_VAULT_PATH:-\$BRAIN_VAULT}"
export OBSIDIAN_WIKI_REPO="\${OBSIDIAN_WIKI_REPO:-\$BRAIN_ROOT}"
export OBSIDIAN_LINK_FORMAT="\${OBSIDIAN_LINK_FORMAT:-wikilink}"
case ":\$PATH:" in
  *":$PREFIX:"*) ;;
  *) export PATH="$PREFIX:\$PATH" ;;
esac
alias codex='brain codex'
alias opencode='brain opencode'
alias claude='brain claude'
alias gemini='brain gemini'
# <<< Agent Brain Runtime <<<
EOF
fi

echo "Agent Brain Runtime installed."
echo "Brain root:  $BRAIN_ROOT"
echo "Brain vault: $BRAIN_VAULT"
echo "Shim:        $PREFIX/brain"

if [ "${INSTALL_AGENT_WRAPPERS:-0}" = "1" ]; then
  for name in codex opencode claude gemini; do
    if command -v "$name" >/dev/null 2>&1; then
      PREFIX="$PREFIX" "$REPO_DIR/scripts/install-agent-wrapper.sh" "$name" || true
    fi
  done
fi

echo
echo "Open a new terminal, then run:"
echo "  brain doctor"
