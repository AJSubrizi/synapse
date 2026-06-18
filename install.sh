#!/usr/bin/env bash
set -euo pipefail

# Check for Python 3 (required for validate.py, dedup.py, skill.py)
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required for Synapse tools (validate.py, dedup.py, skill.py)." >&2
  echo "Install Python 3 and retry." >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local/bin}"
# Canonical home: SYNAPSE_HOME. BRAIN_ROOT/BRAIN_HOME kept as legacy fallbacks.
BRAIN_ROOT="${BRAIN_ROOT:-${SYNAPSE_HOME:-${BRAIN_HOME:-$HOME/Synapse}}}"
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
  else
    # Skip if file exists to avoid overwriting user files (e.g., ~/AGENTS.md)
    printf 'synapse: skipping existing file: %s\n' "$dst" >&2
  fi
}

cp "$REPO_DIR/bin/synapse" "$PREFIX/synapse"
chmod +x "$PREFIX/synapse"
ln -sf synapse "$PREFIX/brain"

if [ ! -d "$BRAIN_VAULT" ]; then
  mkdir -p "$BRAIN_ROOT"
  cp -R "$REPO_DIR/templates/vault" "$BRAIN_VAULT"
fi

mkdir -p \
  "$BRAIN_VAULT/_meta" \
  "$BRAIN_VAULT/_meta/hooks" \
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
copy_if_missing "$REPO_DIR/templates/vault/_meta/skill.py" "$BRAIN_VAULT/_meta/skill.py"
copy_if_missing "$REPO_DIR/templates/vault/_meta/search.py" "$BRAIN_VAULT/_meta/search.py"
copy_if_missing "$REPO_DIR/templates/vault/_meta/hooks/stop-check.sh" "$BRAIN_VAULT/_meta/hooks/stop-check.sh"
copy_if_missing "$REPO_DIR/templates/vault/_meta/hooks/session-enforce.sh" "$BRAIN_VAULT/_meta/hooks/session-enforce.sh"
copy_if_missing "$REPO_DIR/templates/vault/concepts/workflow.md" "$BRAIN_VAULT/concepts/workflow.md"
copy_if_missing "$REPO_DIR/templates/vault/skills/distill-after-work.md" "$BRAIN_VAULT/skills/distill-after-work.md"
copy_if_missing "$REPO_DIR/templates/vault/skills/file-into-vault.md" "$BRAIN_VAULT/skills/file-into-vault.md"
chmod +x "$BRAIN_VAULT/_meta/validate.py" "$BRAIN_VAULT/_meta/dedup.py" "$BRAIN_VAULT/_meta/skill.py" "$BRAIN_VAULT/_meta/search.py"
chmod +x "$BRAIN_VAULT/_meta/hooks/stop-check.sh" "$BRAIN_VAULT/_meta/hooks/session-enforce.sh" 2>/dev/null || true

copy_if_missing "$REPO_DIR/templates/AGENTS.md" "$HOME/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/CLAUDE.md" "$HOME/CLAUDE.md"
copy_if_missing "$REPO_DIR/templates/GEMINI.md" "$HOME/GEMINI.md"

# Stash the context-file templates so `synapse setup <target>` works post-install
# (the installed CLI has no repo checkout beside it).
mkdir -p "$BRAIN_ROOT/templates"
copy_if_missing "$REPO_DIR/templates/AGENTS.md" "$BRAIN_ROOT/templates/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/CLAUDE.md" "$BRAIN_ROOT/templates/CLAUDE.md"
copy_if_missing "$REPO_DIR/templates/GEMINI.md" "$BRAIN_ROOT/templates/GEMINI.md"

BRAIN_ROOT="$BRAIN_ROOT" BRAIN_VAULT="$BRAIN_VAULT" SHELL_RC="$SHELL_RC" \
  "$PREFIX/synapse" reinit >/dev/null

echo "Synapse installed."
echo "Home:   $BRAIN_ROOT"
echo "Vault:  $BRAIN_VAULT"
echo "CLI:    $PREFIX/synapse (brain -> synapse symlink)"

if [ "${INSTALL_AGENT_WRAPPERS:-0}" = "1" ]; then
  for name in codex opencode claude gemini; do
    if command -v "$name" >/dev/null 2>&1; then
      PREFIX="$PREFIX" "$REPO_DIR/scripts/install-agent-wrapper.sh" "$name" || true
    fi
  done
fi

echo
echo "Open a new terminal, then run:"
echo "  synapse doctor"
