#!/usr/bin/env bash
# Synapse one-line installer.
#
#   curl -fsSL https://raw.githubusercontent.com/AJSubrizi/synapse/main/scripts/get.sh | bash
#
# Clones (or updates) the repo into a cache dir, then runs install.sh. Honors the same
# env overrides as install.sh (SYNAPSE_HOME, BRAIN_VAULT, PREFIX, SHELL_RC), plus:
#   SYNAPSE_REPO  git URL to clone   (default: the public repo)
#   SYNAPSE_SRC   where to clone it  (default: ~/.synapse-src)
set -euo pipefail

REPO="${SYNAPSE_REPO:-https://github.com/AJSubrizi/synapse.git}"
SRC="${SYNAPSE_SRC:-$HOME/.synapse-src}"

if ! command -v git >/dev/null 2>&1; then
  printf 'synapse: git is required to install\n' >&2
  exit 1
fi

if [ -d "$SRC/.git" ]; then
  printf 'synapse: updating existing checkout in %s\n' "$SRC"
  git -C "$SRC" pull --ff-only
else
  printf 'synapse: cloning %s -> %s\n' "$REPO" "$SRC"
  git clone --depth 1 "$REPO" "$SRC"
fi

cd "$SRC"
exec ./install.sh
