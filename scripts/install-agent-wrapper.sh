#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local/bin}"
NAME="${1:-}"
REAL_PATH="${2:-}"

if [ -z "$NAME" ]; then
  echo "Usage: scripts/install-agent-wrapper.sh <command-name> [real-path]" >&2
  echo "Example: scripts/install-agent-wrapper.sh codex /path/to/real/codex" >&2
  exit 2
fi

mkdir -p "$PREFIX/.synapse-real"
REAL_STORE="$PREFIX/.synapse-real"
# migrate legacy store
if [ -d "$PREFIX/.brain-real" ] && [ ! -d "$REAL_STORE" ]; then
  mv "$PREFIX/.brain-real" "$REAL_STORE"
fi

if [ -z "$REAL_PATH" ]; then
  REAL_PATH="$(command -v "$NAME" || true)"
fi

if [ -z "$REAL_PATH" ]; then
  echo "Cannot find real command for: $NAME" >&2
  exit 1
fi

if [ "$REAL_PATH" = "$PREFIX/$NAME" ]; then
  if [ -e "$PREFIX/.synapse-real/$NAME" ]; then
    REAL_PATH="$PREFIX/.synapse-real/$NAME"
  else
    echo "$PREFIX/$NAME already exists and no preserved real binary was found." >&2
    echo "Pass the real path explicitly." >&2
    exit 1
  fi
fi

if [ -L "$PREFIX/$NAME" ]; then
  ln -sfn "$(readlink "$PREFIX/$NAME")" "$PREFIX/.synapse-real/$NAME"
  rm "$PREFIX/$NAME"
elif [ -e "$PREFIX/$NAME" ]; then
  mv "$PREFIX/$NAME" "$PREFIX/.synapse-real/$NAME"
else
  ln -sfn "$REAL_PATH" "$PREFIX/.synapse-real/$NAME"
fi

cat > "$PREFIX/$NAME" <<EOF
#!/usr/bin/env bash
# Synapse wrapper — skip second pass if env already loaded.
if [[ "\${BRAIN_ACTIVE:-0}" == "1" ]]; then
  exec "$REAL_PATH" "\$@"
fi
if command -v "$PREFIX/synapse" >/dev/null 2>&1; then
  exec "$PREFIX/synapse" "$REAL_PATH" "\$@"
fi
exec "$PREFIX/brain" "$REAL_PATH" "\$@"
EOF

chmod +x "$PREFIX/$NAME"

echo "Installed synapse wrapper: $PREFIX/$NAME -> $REAL_PATH"

