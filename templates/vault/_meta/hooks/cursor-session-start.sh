#!/usr/bin/env bash
# Cursor sessionStart hook — inject vault bootstrap (hot + digest head + optional query).
# Stdin: JSON {session_id, ...}. Stdout: JSON {additional_context, env}.
# Never blocks session creation. Degrades to {} if python/engine missing.
set -u

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META="$(cd "$SELF/.." && pwd)"

command -v python3 >/dev/null 2>&1 || { echo '{}'; exit 0; }
[ -f "$META/search.py" ] || { echo '{}'; exit 0; }

input="$(cat 2>/dev/null || true)"
printf '%s' "$input" | META="$META" VAULT="$(cd "$META/.." && pwd)" python3 -c '
import json, os, sys
meta = os.environ["META"]
vault = os.environ["VAULT"]
sys.path.insert(0, meta)
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
lines = ["<synapse-memory>",
         "Session bootstrap from your Synapse vault. Prefer these notes over re-deriving.",
         f"Vault: {vault}", ""]
hot = os.path.join(vault, "hot.md")
if os.path.isfile(hot):
    lines.append("## hot.md")
    lines.append(open(hot, encoding="utf-8").read().strip()[:2000])
    lines.append("")
digest = os.path.join(meta, "digest.md")
catalog = os.path.join(meta, "catalog.md")
for path, title in ((digest, "digest"), (catalog, "catalog")):
    if os.path.isfile(path):
        body = open(path, encoding="utf-8").read().strip()
        lines.append(f"## {title} (head)")
        lines.append("\n".join(body.splitlines()[:40]))
        lines.append("")
        break
# Optional boot query from env
q = (os.environ.get("SYNAPSE_BOOT_QUERY") or "").strip()
if len(q) >= 3:
    try:
        import contextlib, io, search
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            search.cmd_query(q, 5)
        out = buf.getvalue().strip()
        if out and not out.startswith("no matches"):
            lines.append(f"## query: {q}")
            lines.append(out)
            lines.append("")
    except Exception:
        pass
lines.append("Run `synapse query <topic>` each turn for fresh recall; distill after meaningful work.")
lines.append("</synapse-memory>")
ctx = "\n".join(lines)
payload = {
    "additional_context": ctx,
    "env": {
        "BRAIN_VAULT": vault,
        "SYNAPSE_SESSION_ID": str(data.get("session_id") or ""),
        "BRAIN_LOADED": "1",
    },
}
print(json.dumps(payload))
'
