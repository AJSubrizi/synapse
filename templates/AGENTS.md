# AGENTS.md — Synapse bootstrap

The vault is an **LLM Wiki** (Karpathy's pattern): immutable `raw/` sources, an LLM-owned
wiki, and a schema in `$BRAIN_VAULT/AGENTS.md`. Operations: ingest → query → lint.

Query the vault before meaningful work (all task types: coding, design, debug, knowledge).

1. Open `$BRAIN_VAULT/AGENTS.md` and `$BRAIN_VAULT/index.md` (or Phase 0-short per workflow).
2. Choose relevant notes; use `summary:` before full bodies (`synapse query` to rank).
3. After **meaningful work**, ingest external sources (`synapse ingest`) and distill
   reusable knowledge into the wiki.
4. Run `synapse lint` (or `python3 "$BRAIN_VAULT/_meta/validate.py"`).

**Meaningful work** = new pattern/decision, non-obvious fix, knowledge not in vault, infra
setup, or skill outcome worth remembering. Skip distillation for typos and purely
executional tasks.

Recommended: RTK for shell commands; Synapse before planning, editing, or project output.
