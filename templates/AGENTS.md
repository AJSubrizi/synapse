# AGENTS.md — Synapse bootstrap

The vault is an **LLM Wiki** (Karpathy's pattern): immutable `raw/` sources, an LLM-owned
wiki, and a schema in `$BRAIN_VAULT/AGENTS.md`. Operations: ingest → query → lint.

## Continuous loop (Codex / OpenCode / any AGENTS.md consumer)

**Phase 0 — before meaningful work**

1. `synapse status` (expect usable vault paths).
2. `synapse query "<user topic>"` (falls back to lexical search if no index).
3. Read `summary:` on top hits; open bodies only when needed. Cite `[[page-name]]`.

**Phase 2 — after meaningful work**

1. Search first: `synapse search "<topic>"` — prefer update over near-duplicates.
2. File or refresh: `synapse file <category> <title>` or `synapse file update <stem>`.
3. `synapse lint --strict` → fix every finding → re-run until clean.

**Meaningful work** = new pattern/decision, non-obvious fix, knowledge not in vault, infra
setup, or skill outcome worth remembering. Skip for typos and purely executional tasks.

Recommended: RTK for shell commands. Cursor: `synapse setup cursor`. Claude Code:
`synapse hooks install` (or `synapse onboard`). OpenCode: `synapse setup opencode`
(writes `AGENTS.md` + `opencode.json` instructions).
