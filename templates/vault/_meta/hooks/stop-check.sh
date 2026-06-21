#!/usr/bin/env bash
# Claude Code Stop / SubagentStop hook — close the Synapse loop:
#   - notes changed this session   -> run `synapse check`; block the stop if it errors.
#   - project changed, no new notes -> one-shot reminder to distill what was learned.
# Guarded by stop_hook_active so it never loops. Silence the distill nudge with
# SYNAPSE_DISTILL_NUDGE=0. A no-op when the vault isn't under git.
set -u

input="$(cat 2>/dev/null || true)"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(cd "$SELF/../.." && pwd)"        # _meta/hooks -> vault
export BRAIN_VAULT="$VAULT"
export BRAIN_SKILLS_DIR="${BRAIN_SKILLS_DIR:-$VAULT/skills}"

field() {
  printf '%s' "$input" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get(sys.argv[1],"") or "")' "$1" 2>/dev/null
}

# Fresh process per call; this guard is what stops an infinite stop loop.
case "$(field stop_hook_active)" in True|true) exit 0 ;; esac
cwd="$(field cwd)"

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

if is_dirty "$VAULT" -- .; then
  report="$(run_check 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    { printf 'Synapse: the vault has quality issues — fix them before finishing.\n\n'
      printf '%s\n' "$report"; } >&2
    exit 2
  fi
  exit 0
fi

if [ "${SYNAPSE_DISTILL_NUDGE:-1}" != "0" ] && [ -n "$cwd" ] && is_dirty "$cwd" -- .; then
  { printf 'Synapse: you changed project files but wrote no vault notes this session.\n'
    printf 'If this produced reusable knowledge (a non-obvious fix, a new pattern or\n'
    printf 'decision, project/infra setup), distill it into the vault now per\n'
    printf '%s/_meta/workflow.md, then finish. If the task was trivial, just stop again.\n' "$VAULT"
  } >&2
  exit 2
fi

exit 0
