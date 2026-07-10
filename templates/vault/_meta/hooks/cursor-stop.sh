#!/usr/bin/env bash
# Cursor stop hook — close the Synapse loop (Claude stop-check parity, Cursor-shaped).
# Stdin: JSON {status, loop_count, cwd?, workspace_roots?}.
# Stdout: optional {followup_message} (Cursor cannot hard-block like Claude exit 2).
# Silence distill nudge with SYNAPSE_DISTILL_NUDGE=0. Caps via Cursor loop_limit.
set -u

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META="$(cd "$SELF/.." && pwd)"
VAULT="$(cd "$META/.." && pwd)"
export BRAIN_VAULT="$VAULT"
export BRAIN_SKILLS_DIR="${BRAIN_SKILLS_DIR:-$VAULT/skills}"

input="$(cat 2>/dev/null || true)"

is_dirty() {  # returns 0 if repo at $1 has changes under the trailing pathspec
  local d="$1"; shift
  git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 1
  git -C "$d" diff --quiet "$@" 2>/dev/null || return 0
  git -C "$d" diff --cached --quiet "$@" 2>/dev/null || return 0
  [ -n "$(git -C "$d" ls-files --others --exclude-standard "$@" 2>/dev/null)" ] && return 0
  return 1
}

run_check() {
  if command -v synapse >/dev/null 2>&1; then synapse check
  elif command -v brain >/dev/null 2>&1; then brain check
  elif command -v python3 >/dev/null 2>&1; then python3 "$VAULT/_meta/validate.py"
  else return 0; fi
}

# Parse status / loop_count / cwd via python (Cursor payload varies by version)
# shellcheck disable=SC2016  # the python program is intentionally a literal (no shell expansion)
eval "$(printf '%s' "$input" | python3 -c '
import json, os, shlex, sys
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
status = data.get("status") or "completed"
loop = int(data.get("loop_count") or 0)
cwd = data.get("cwd") or data.get("workspace_root") or ""
if not cwd:
    roots = data.get("workspace_roots") or data.get("roots") or []
    if isinstance(roots, list) and roots:
        cwd = roots[0] if isinstance(roots[0], str) else ""
if not cwd:
    cwd = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("PWD") or ""
print("STATUS=" + shlex.quote(str(status)))
print("LOOP=" + shlex.quote(str(loop)))
print("CWD=" + shlex.quote(str(cwd)))
' 2>/dev/null || echo 'STATUS=completed; LOOP=0; CWD=')"

# Only act on a completed agent turn, first auto-followup slot
[ "$STATUS" = "completed" ] || [ "$STATUS" = "" ] || { echo '{}'; exit 0; }
[ "${LOOP:-0}" -gt 0 ] 2>/dev/null && { echo '{}'; exit 0; }

emit() {
  python3 -c 'import json,sys; print(json.dumps({"followup_message": sys.argv[1]}))' "$1"
}

# Vault dirty → lint; ask agent to fix before finishing
if is_dirty "$VAULT" -- .; then
  report="$(run_check 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    emit "Synapse: vault has quality issues — fix them before finishing, then stop again.

${report}"
    exit 0
  fi
  echo '{}'
  exit 0
fi

# Project dirty, no vault notes this session → distill nudge
if [ "${SYNAPSE_DISTILL_NUDGE:-1}" != "0" ] && [ -n "${CWD:-}" ] && [ "$CWD" != "$VAULT" ] \
   && is_dirty "$CWD" -- .; then
  emit "Synapse: you changed project files but wrote no vault notes this session.
If this produced reusable knowledge (pattern, decision, non-obvious fix), distill now:
  synapse file <category> <title>   # or: synapse file update <stem>
  synapse lint --strict
Vault: ${VAULT}
Reply DONE if nothing meaningful to distill."
  exit 0
fi

# Fallback gentle nudge when we cannot see project git (still once per stop)
if [ "${SYNAPSE_DISTILL_NUDGE:-1}" != "0" ] && [ -z "${CWD:-}" ]; then
  emit "Synapse close-loop check: if this session produced reusable knowledge, distill with \`synapse file\` / \`file update\`, then \`synapse lint --strict\`. Vault: ${VAULT}. Reply DONE if nothing to distill."
  exit 0
fi

echo '{}'
exit 0
