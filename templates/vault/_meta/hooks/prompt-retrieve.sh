#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook — surface relevant vault notes for *every* prompt,
# turning Phase-0's one-shot read into continuous, per-turn retrieval. Cheap on purpose:
# uses the instant lexical (frontmatter-weighted) ranker, never loads an embedding model.
# Degrades to a no-op if python3 / the engine is missing, and never blocks the prompt.
set -u

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META="$(cd "$SELF/.." && pwd)"            # hooks -> _meta

command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$META/search.py" ] || exit 0

input="$(cat 2>/dev/null || true)"
# shellcheck disable=SC2016  # the python program is intentionally a literal (no shell expansion)
printf '%s' "$input" | META="$META" python3 -c '
import contextlib, io, json, os, re, sys
sys.path.insert(0, os.environ["META"])
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
prompt = (data.get("prompt") or "").strip()
if len(prompt) < 4:
    sys.exit(0)
try:
    import search
except Exception:
    sys.exit(0)
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        search.cmd_search(prompt, 3, True)   # instant lexical ranking, no model
except Exception:
    sys.exit(0)
out = buf.getvalue().strip()
if not out or out.startswith("no matches"):
    sys.exit(0)
ctx = ("<synapse-memory>\n"
       "Notes already in your vault that may be relevant to this request — read the ones "
       "that apply before answering, and reuse them instead of re-deriving:\n"
       + out +
       "\nRun `synapse query <topic>` for deeper (semantic) recall; distill any new, "
       "non-obvious learning back into the vault afterward.\n"
       "</synapse-memory>")
# A short, visible signal that memory fired (the full context is injected silently).
stems = [os.path.splitext(os.path.basename(r))[0] for r in re.findall(r"(\S+\.md)", out)]
payload = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
if stems:
    payload["systemMessage"] = ("\U0001f9e0 Synapse: " + str(len(stems)) +
                                " note rilevanti — " + ", ".join(stems[:3]))
print(json.dumps(payload))
'
