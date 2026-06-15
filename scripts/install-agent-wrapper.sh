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

mkdir -p "$PREFIX/.brain-real"

if [ -z "$REAL_PATH" ]; then
  REAL_PATH="$(command -v "$NAME" || true)"
fi

if [ -z "$REAL_PATH" ]; then
  echo "Cannot find real command for: $NAME" >&2
  exit 1
fi

if [ "$REAL_PATH" = "$PREFIX/$NAME" ]; then
  if [ -e "$PREFIX/.brain-real/$NAME" ]; then
    REAL_PATH="$PREFIX/.brain-real/$NAME"
  else
    echo "$PREFIX/$NAME already exists and no preserved real binary was found." >&2
    echo "Pass the real path explicitly." >&2
    exit 1
  fi
fi

if [ -L "$PREFIX/$NAME" ]; then
  ln -sfn "$(readlink "$PREFIX/$NAME")" "$PREFIX/.brain-real/$NAME"
  rm "$PREFIX/$NAME"
elif [ -e "$PREFIX/$NAME" ]; then
  mv "$PREFIX/$NAME" "$PREFIX/.brain-real/$NAME"
else
  ln -sfn "$REAL_PATH" "$PREFIX/.brain-real/$NAME"
fi

cat > "$PREFIX/$NAME" <<EOF
#!/usr/bin/env bash
# If brain already set up the environment (e.g. invoked via the shell alias),
# skip the second pass and run the real command directly.
if [[ "\${BRAIN_ACTIVE:-0}" == "1" ]]; then
  exec "$REAL_PATH" "\$@"
fi
exec "$PREFIX/brain" "$REAL_PATH" "\$@"
EOF

chmod +x "$PREFIX/$NAME"

echo "Installed brain wrapper: $PREFIX/$NAME -> $REAL_PATH"

