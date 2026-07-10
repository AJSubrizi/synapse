#!/usr/bin/env bash
# Cursor stop hook — nudge distillation once when the agent loop ends.
# Stdin: JSON {status, loop_count}. Stdout: optional {followup_message}.
# Silence with SYNAPSE_DISTILL_NUDGE=0. Caps via Cursor loop_limit.
set -u

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META="$(cd "$SELF/.." && pwd)"
VAULT="$(cd "$META/.." && pwd)"

[ "${SYNAPSE_DISTILL_NUDGE:-1}" = "0" ] && { echo '{}'; exit 0; }

input="$(cat 2>/dev/null || true)"
printf '%s' "$input" | VAULT="$VAULT" python3 -c '
import json, os, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    raise SystemExit(0)
if data.get("status") not in (None, "completed"):
    print("{}")
    raise SystemExit(0)
# Only nudge on the first auto-followup opportunity
if int(data.get("loop_count") or 0) > 0:
    print("{}")
    raise SystemExit(0)
vault = os.environ["VAULT"]
# Heuristic: if log.md was not touched recently and project likely changed, nudge.
msg = (
    "Synapse close-loop check: if this session produced a reusable pattern, decision, "
    "or non-obvious fix, distill it now with `synapse file <category> <title>` "
    "(or `synapse file update <stem>`), then `synapse lint --strict`. "
    f"Vault: {vault}. Reply DONE if nothing meaningful to distill."
)
print(json.dumps({"followup_message": msg}))
'
