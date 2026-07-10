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

# Engine files are always refreshed from the repo (vault content is never touched).
sync_engine() {
  local src="$1"
  local dst="$2"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

cp "$REPO_DIR/bin/synapse" "$PREFIX/synapse"
chmod +x "$PREFIX/synapse"
ln -sf synapse "$PREFIX/brain"

if [ ! -d "$BRAIN_VAULT" ]; then
  mkdir -p "$BRAIN_ROOT"
  cp -R "$REPO_DIR/templates/vault" "$BRAIN_VAULT"
fi

# LLM Wiki layout: immutable raw/ + core wiki categories + ingest target (sources/).
# Optional categories (people/organizations/analysis/journal) are created on demand.
mkdir -p \
  "$BRAIN_VAULT/_meta" \
  "$BRAIN_VAULT/_meta/hooks" \
  "$BRAIN_VAULT/raw" \
  "$BRAIN_VAULT/sources" \
  "$BRAIN_VAULT/concepts" \
  "$BRAIN_VAULT/techniques" \
  "$BRAIN_VAULT/projects" \
  "$BRAIN_VAULT/skills"

copy_if_missing "$REPO_DIR/templates/vault/AGENTS.md" "$BRAIN_VAULT/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/vault/index.md" "$BRAIN_VAULT/index.md"
copy_if_missing "$REPO_DIR/templates/vault/hot.md" "$BRAIN_VAULT/hot.md"
copy_if_missing "$REPO_DIR/templates/vault/log.md" "$BRAIN_VAULT/log.md"
# Schema docs: refresh workflow/taxonomy from repo; keep user categories if present
sync_engine "$REPO_DIR/templates/vault/_meta/workflow.md" "$BRAIN_VAULT/_meta/workflow.md"
sync_engine "$REPO_DIR/templates/vault/_meta/taxonomy.md" "$BRAIN_VAULT/_meta/taxonomy.md"
copy_if_missing "$REPO_DIR/templates/vault/_meta/categories" "$BRAIN_VAULT/_meta/categories"
sync_engine "$REPO_DIR/templates/vault/_meta/vault_config.py" "$BRAIN_VAULT/_meta/vault_config.py"
sync_engine "$REPO_DIR/templates/vault/_meta/validate.py" "$BRAIN_VAULT/_meta/validate.py"
sync_engine "$REPO_DIR/templates/vault/_meta/dedup.py" "$BRAIN_VAULT/_meta/dedup.py"
sync_engine "$REPO_DIR/templates/vault/_meta/skill.py" "$BRAIN_VAULT/_meta/skill.py"
sync_engine "$REPO_DIR/templates/vault/_meta/search.py" "$BRAIN_VAULT/_meta/search.py"
sync_engine "$REPO_DIR/templates/vault/_meta/wiki.py" "$BRAIN_VAULT/_meta/wiki.py"
sync_engine "$REPO_DIR/templates/vault/_meta/metrics.py" "$BRAIN_VAULT/_meta/metrics.py"
sync_engine "$REPO_DIR/templates/vault/_meta/ENGINE_VERSION" "$BRAIN_VAULT/_meta/ENGINE_VERSION"
sync_engine "$REPO_DIR/templates/vault/_meta/hooks/stop-check.sh" "$BRAIN_VAULT/_meta/hooks/stop-check.sh"
sync_engine "$REPO_DIR/templates/vault/_meta/hooks/session-enforce.sh" "$BRAIN_VAULT/_meta/hooks/session-enforce.sh"
sync_engine "$REPO_DIR/templates/vault/_meta/hooks/prompt-retrieve.sh" "$BRAIN_VAULT/_meta/hooks/prompt-retrieve.sh"
copy_if_missing "$REPO_DIR/templates/vault/concepts/workflow.md" "$BRAIN_VAULT/concepts/workflow.md"
copy_if_missing "$REPO_DIR/templates/vault/skills/distill-after-work.md" "$BRAIN_VAULT/skills/distill-after-work.md"
copy_if_missing "$REPO_DIR/templates/vault/skills/file-into-vault.md" "$BRAIN_VAULT/skills/file-into-vault.md"
[ -f "$BRAIN_VAULT/raw/README.md" ] || copy_if_missing "$REPO_DIR/templates/vault/raw/README.md" "$BRAIN_VAULT/raw/README.md"
chmod +x "$BRAIN_VAULT/_meta/validate.py" "$BRAIN_VAULT/_meta/dedup.py" "$BRAIN_VAULT/_meta/skill.py" \
         "$BRAIN_VAULT/_meta/search.py" "$BRAIN_VAULT/_meta/wiki.py" "$BRAIN_VAULT/_meta/metrics.py" 2>/dev/null || true
chmod +x "$BRAIN_VAULT/_meta/hooks/stop-check.sh" "$BRAIN_VAULT/_meta/hooks/session-enforce.sh" \
         "$BRAIN_VAULT/_meta/hooks/prompt-retrieve.sh" 2>/dev/null || true

copy_if_missing "$REPO_DIR/templates/AGENTS.md" "$HOME/AGENTS.md"
copy_if_missing "$REPO_DIR/templates/CLAUDE.md" "$HOME/CLAUDE.md"
copy_if_missing "$REPO_DIR/templates/GEMINI.md" "$HOME/GEMINI.md"

# Stash templates so `synapse setup` / `upgrade` / `onboard` work post-install
# (the installed CLI has no repo checkout beside it).
mkdir -p "$BRAIN_ROOT/templates/vault/_meta/hooks" "$BRAIN_ROOT/templates/cursor" \
         "$BRAIN_ROOT/templates/vault/skills" \
         "$BRAIN_ROOT/templates/examples/distillation/after"
sync_engine "$REPO_DIR/templates/AGENTS.md" "$BRAIN_ROOT/templates/AGENTS.md"
sync_engine "$REPO_DIR/templates/CLAUDE.md" "$BRAIN_ROOT/templates/CLAUDE.md"
sync_engine "$REPO_DIR/templates/GEMINI.md" "$BRAIN_ROOT/templates/GEMINI.md"
sync_engine "$REPO_DIR/templates/cursor/synapse.mdc" "$BRAIN_ROOT/templates/cursor/synapse.mdc"
# Full engine tree for upgrade_cmd
for f in validate.py dedup.py skill.py search.py wiki.py metrics.py vault_config.py \
         synapse_lib.py pack.py \
         workflow.md taxonomy.md categories ENGINE_VERSION; do
  sync_engine "$REPO_DIR/templates/vault/_meta/$f" "$BRAIN_ROOT/templates/vault/_meta/$f"
done
sync_engine "$REPO_DIR/templates/vault/_meta/synapse_lib.py" "$BRAIN_VAULT/_meta/synapse_lib.py"
sync_engine "$REPO_DIR/templates/vault/_meta/pack.py" "$BRAIN_VAULT/_meta/pack.py"
for f in session-enforce.sh prompt-retrieve.sh stop-check.sh; do
  sync_engine "$REPO_DIR/templates/vault/_meta/hooks/$f" "$BRAIN_ROOT/templates/vault/_meta/hooks/$f"
done
for f in distill-after-work.md file-into-vault.md; do
  copy_if_missing "$REPO_DIR/templates/vault/skills/$f" "$BRAIN_ROOT/templates/vault/skills/$f"
done
# Seed examples for onboard
if [ -d "$REPO_DIR/examples/distillation/after" ]; then
  cp -R "$REPO_DIR/examples/distillation/after/." "$BRAIN_ROOT/templates/examples/distillation/after/"
fi

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
echo "  synapse onboard          # setup Claude + Cursor, hooks, seed demo notes, doctor"
echo "  # or: synapse doctor"
